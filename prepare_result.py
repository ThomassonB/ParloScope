from read_interview import Interval, TimeStamp, InterruptionCheckpoint
from read_interview import Interview, ExcludedIntervals, SpeechIntervals, InterruptionCounts, Notes

class Result:
    title: str
    target_speaker: str
    duration: Interval
    breaks: list[Interval]
    speaker_time: list[Interval]
    disruptions: list[InterruptionCheckpoint]
    warnings: str

    def __init__(self, data):
        self.title = data.get('title', 'Analyse de l’interview')
        self.target_speaker = data['target_speaker']

        self.duration = interview_interval(data)

        self.breaks = get_breaks(data)

        self.effective_duration = self.duration.duration() - Interval.sum(self.breaks)

        self.speaker_time = get_speech(data)
        self.disruptions = get_disruptions(data)

        self.normalise()

        # self.warnings = collect_warnings(data, analysis, speech, previous, following)

    def no_break_duration(self) -> TimeStamp:
        start = self.duration.start
        end = self.duration.end - Interval.sum(self.breaks)
        if start >= end:
            raise ValueError(f"Temps de pause plus longue que le temps de l'interview")
        return TimeStamp.from_seconds((end - start).time)

    def get_statistics_by_minutes(self):
        """Calcule le temps de parole pour chaque minute d’interview, sur la chronologie sans pauses"""
        minutes = []
        effective_speak = self.get_effective_speak()

        for start in range(0, self.effective_duration.time, 60):
            window = Interval(
                TimeStamp.from_seconds(start), 
                TimeStamp.from_seconds(min(start + 60, self.effective_duration.time))
                )
            
            spoken = sum(window.overlap_time(interval)
                          for interval in effective_speak)

            minutes.append({
                'interval': window,
                'speech_time': spoken,
                'speech_percentage': 100 * spoken.time / window.duration().time,
            })
        return minutes

    def get_effective_speak(self):
        """Retourne une liste d'intervalles sur la chronologie effective"""

        time_to_remove = self.duration.start
        effective_speak = []
        pause_idx = 0

        for interval in self.speaker_time:
            if pause_idx < len(self.breaks) and interval.start >= self.breaks[pause_idx].end:
                time_to_remove += self.breaks[pause_idx].duration()
                pause_idx += 1

            effective_speak.append(interval.made_in_heaven(time_to_remove))
        return effective_speak

    def normalise(self):
        """Retire les pauses de l’axe temporel et renvoie la durée effective d'un temps de parole"""
        for speech in self.speaker_time[:]:
            for pause in self.breaks:

                if speech.overlap_time(pause).time == 0:
                    continue

                self.speaker_time.append(int for int in speech.substract(pause) if int.duration != 0)
                self.speaker_time.remove(speech)
                
        self.speaker_time = sorted(self.speaker_time)


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

def interview_interval(data) -> Interval:
    return Interval(TimeStamp(data[Interview.name]['start']), TimeStamp(data[Interview.name]['end']))

def get_breaks(data) -> list[Interval]:
    segments = [Interval(TimeStamp(pause["start"]), TimeStamp(pause["end"])) 
                for pause in data[ExcludedIntervals.name]]
    return merge_intervals(segments)

def get_speech(data) -> list[Interval]:
    segments = [Interval(TimeStamp(time["start"]), TimeStamp(time["end"])) 
                for time in data[SpeechIntervals.name] 
                if time["speaker"] == data["target_speaker"]
                ]    
    return merge_intervals(segments)

def get_disruptions(data) -> list[InterruptionCheckpoint]:
    return [InterruptionCheckpoint(time=TimeStamp(element["time"]), count=element["count"]) 
            for element in data[InterruptionCounts.name]]

def get_result(data):
    return Result(data)
