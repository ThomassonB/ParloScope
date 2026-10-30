from read_interview import Interval, TimeStamp, InterruptionCheckpoint
from read_interview import Interview, ExcludedIntervals, SpeechIntervals, InterruptionCounts, Notes

from itertools import product


def interview_interval(data) -> Interval:
    return Interval(TimeStamp(data[Interview.name]['start']), TimeStamp(data[Interview.name]['end']))


def analysis_interval(interview: Interval, endpoint=None) -> Interval:
    end = interview.end if endpoint is None else TimeStamp(endpoint)

    if not interview.start <= end <= interview.end:
        raise ValueError(f'L’horodatage [endpoint] doit être compris entre {interview.start.format_duration()} et {interview.end.format_duration()}.')
    
    return Interval(interview.start, end)


def merge_intervals(intervals) -> list[Interval]:
    """Fusionne les recoupements ; conserve séparés les intervalles qui se touchent."""
    merged = []
    for interval in sorted(intervals):
        if merged and interval.start < merged[-1].end:
            previous = merged[-1]
            merged[-1] = Interval(previous.start, max(previous.end, interval.end))
        else:
            merged.append(interval)
    return merged


def excluded_intervals(data) -> list[Interval]:
    intervals = [Interval(TimeStamp(item['start']), TimeStamp(item['end'])) for item in data[ExcludedIntervals.name]]
    return merge_intervals(intervals)


def speech_intervals(data) -> list[Interval]:
    intervals = [
        Interval(TimeStamp(item['start']), TimeStamp(item['end']))
        for item in data[SpeechIntervals.name]
        if item['speaker'] == data['target_speaker'] and item.get('include', True)
    ]
    return merge_intervals(intervals)

# fonction de nettoyage si le json a mal été rempli
def active_segments(analysis: Interval, excluded:  list[Interval]):
    """Construit des segments en excluant les pauses. excluded est supposé avoir été merged"""
    segments = []
    current = analysis.start
    for pause in excluded:
        clipped = analysis.intersection(pause)

        if clipped is None:
            continue
        
        if current < clipped.start:
            segments.append(Interval(current, clipped.start))

        current = max(current, clipped.end)
    if current < analysis.end:
        segments.append(Interval(current, analysis.end))
    return segments

# fonction de nettoyage si le json a mal été rempli
def clip_speech_to_segments(segments, speech):
    """Conserve les portions parlées dans la vidéo hors pauses"""

    intersections = map(
                        lambda pair: pair[0].intersection(pair[1]),
                        product(segments, speech),
                    )

    return sorted(intersection for intersection in intersections if intersection is not None)

# fonction de nettoyage si le json a mal été rempli
def build_effective_timeline(segments, speech) -> tuple[list[Interval], Interval]:
    """Retire les pauses de l’axe temporel et renvoie la durée effective d'un temps de parole"""
    effective_speech = []
    duration = TimeStamp("0:00")
    for segment in segments:
        for interval in speech:
            intersection = segment.intersection(interval)
            if intersection is None:
                continue
            
            effective_speech.append(Interval(
                duration + (intersection.start - segment.start),
                duration + (intersection.end - segment.start),
            ))

        duration += segment.duration()
    return sorted(effective_speech), Interval(TimeStamp("0:00"), duration)
# fin des fonctions de nettoyage 

def interruption_checkpoints(data) -> list[InterruptionCheckpoint]:
    return sorted(InterruptionCheckpoint(TimeStamp(item['time']), item['count'])
                    for item in data[InterruptionCounts.name])


def interruption_bounds(checkpoints, time):
    previous = max(point for point in checkpoints if point.time <= time)
    following = min(point for point in checkpoints if point.time >= time)
    return previous, following


def overlap_duration(first: Interval, second: Interval) -> TimeStamp:
    intersection = first.intersection(second)
    return intersection.duration() if intersection is not None else None


def calculate_minute_statistics(speech: list[Interval], interview_duration: Interval):
    """Calcule le temps de parole pour chaque minute d’interview, sur la chronologie sans pauses"""
    minutes = []
    for start in range(0, interview_duration.end.time, 60):
        window = Interval(
            TimeStamp.from_seconds(start), 
            TimeStamp.from_seconds(min(start + 60, interview_duration.end.time))
            )
        
        spoken = sum(overlap for interval in speech if (overlap:=overlap_duration(window, interval) is not None))

        minutes.append({
            'minute': start // 60 + 1,
            'effective_start': window.start.format_duration(),
            'effective_end': window.end.format_duration(),
            'observed_duration_seconds': window.duration().time,
            'speech_seconds': spoken,
            'speech_percentage': 100 * spoken / window.duration().time,
        })
    return minutes


def collect_warnings(data, analysis, speech, previous, following):
    warnings = list(data.get('notes', []))
    warnings.append(f'Les minutes commencent à {analysis.start.format_duration()}, interludes exclus. La dernière peut être partielle.')
    
    omitted = [
        item for item in data[SpeechIntervals.name]
        if item['speaker'] == data['target_speaker']
        and not item.get('include', True)
        and TimeStamp(item['start']) < analysis.end
    ]

    for item in omitted:
        warnings.append(f"Parole exclue du calcul : {item['start']} – {item['end']}. {item.get('note', '')}".strip())
    if not speech:
        warnings.append('Aucun intervalle de parole inclus pour la personne cible. Le total décrit uniquement le relevé fourni.')
    if previous.count != following.count:
        warnings.append('Nombre exact d’interruptions inconnu à cet instant : bornes issues des cumuls encadrants, sans interpolation.')
    return warnings, len(omitted)


def serialize(interval):
    return {'start': interval.start.time, 'end': interval.end.time}


def build_chart_data(analysis, active_segments, excluded, video_speech, checkpoints):
    clipped_pauses = [
        intersection for interval in excluded
        if (intersection := analysis.intersection(interval)) is not None
    ]

    return {
        'video_start_seconds': analysis.start.time,
        'video_end_seconds': analysis.end.time,
        'included_segments': [serialize(interval) for interval in active_segments],
        'excluded_segments': [serialize(interval) for interval in clipped_pauses],
        'speech_segments': [serialize(interval) for interval in video_speech],
        'interruption_checkpoints': [{'time': point.time.time, 'count': point.count} 
                                     for point in checkpoints if point.time <= analysis.end],
        'speech_durations_seconds': [interval.duration().time for interval in video_speech],
    }


def build_analysis_result(data, interview, analysis, duration, effective_speech, previous, 
                          following, minutes, warnings, omitted_count, chart_data):
    
    total_speech = sum(interval.duration().time for interval in effective_speech)

    return {
        'title': data.get('title', 'Analyse de l’interview'),
        'target_speaker': data['target_speaker'],
        'video_timestamp': analysis.end.format_duration(),
        'video_start': interview.start.format_duration(),
        'interview_video_end': interview.end.format_duration(),
        'excluded_interlude': (analysis.duration() - duration.end).format_duration(),
        'interview_duration': duration.end.format_duration(),
        'minimum_interruptions': previous.count, 
        'maximum_interruptions': following.count,
        'previous_checkpoint': {'timestamp': previous.time.format_duration(), 
                                'count': previous.count},
        'following_checkpoint': {'timestamp': following.time.format_duration(), 
                                 'count': following.count},
        'minimum_interruptions_per_minute': previous.count * 60 / duration.end.time if duration.end.time > 0 else None,
        'maximum_interruptions_per_minute': following.count * 60 / duration.end.time if duration.end.time > 0 else None,
        'total_speech_seconds': total_speech,
        'speech_percentage': 100 * total_speech / duration.end.time if duration.end.time > 0 else None,
        'speech_by_minute': minutes, 
        'excluded_speech_count': omitted_count,
        'warnings': warnings, 
        'chart_data': chart_data,
    }


def analyze(data, endpoint=None):
    """Orchestre les règles métier ; ne lit ni n’écrit de fichier et ne produit pas de HTML."""
    interview = interview_interval(data)
    analysis = analysis_interval(interview, endpoint)

    excluded = excluded_intervals(data)
    speech = speech_intervals(data)
    segments = active_segments(analysis, excluded)
    video_speech = clip_speech_to_segments(segments, speech)
    effective_speech, duration = build_effective_timeline(segments, video_speech)

    checkpoints = interruption_checkpoints(data)
    previous, following = interruption_bounds(checkpoints, analysis.end)
    minutes = calculate_minute_statistics(effective_speech, duration)
    warnings, omitted_count = collect_warnings(data, analysis, speech, previous, following)
    chart_data = build_chart_data(analysis, segments, excluded, video_speech, checkpoints)

    return build_analysis_result(
        data, interview, analysis, duration, effective_speech,
        previous, following, minutes, warnings, omitted_count, chart_data,
    )