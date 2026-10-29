#!/usr/bin/env python3
import argparse
import json
import re
from html import escape
from pathlib import Path
from string import Template
from typing import NamedTuple

def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Champs JSON répété : {key}.")
        result[key] = value
    return result


def load_interview(path):
    """Charge les données UTF-8 ; refuse les clés répétées et les JSON mal formés."""
    try:
        with open(Path(path).expanduser(), encoding="utf-8") as file:
            data = json.load(file, object_pairs_hook=reject_duplicate_keys)

    except json.JSONDecodeError as error:
        raise ValueError(f"JSON invalide, ligne {error.lineno}, colonne {error.colno} : {error.msg}") from error
    
    return validate_interview(data)

class TimeStamp:
    def __init__(self, text):
        if not isinstance(text, str):
            raise ValueError("L’horodatage doit être une chaîne M:SS ou H:MM:SS.")

        text = text.strip()
        if not re.fullmatch(r"\d+:\d{2}(?::\d{2})?", text):
            raise ValueError("Format attendu : M:SS ou H:MM:SS, par exemple 12:03.")

        parts = [int(p) for p in text.split(":")]
        if any(p >= 60 for p in parts[1:]):
            raise ValueError("Les secondes et les minutes après les heures doivent être inférieures à 60.")
        
        
        self.time = 0
        for component in parts:
            self.time *= 60
            self.time += component
        
        self.text = text

    def __sub__(self, other):
        if not isinstance(other, Interval):
            return NotImplemented
        return self.time - other.time

    def __lt__(self, other):
        if not isinstance(other, Interval):
            return NotImplemented
        return self.time < other.time

    def __gt__(self, other):
        if not isinstance(other, Interval):
            return NotImplemented
        return self.time > other.time

    def __le__(self, other):
        if not isinstance(other, Interval):
            return NotImplemented
        return self.time <= other.time
    
    def __ge__(self, other):
        if not isinstance(other, Interval):
            return NotImplemented
        return self.time >= other.time
        
    def format_duration(self, other):
        minutes, sec = divmod(self - other, 60)
        return f"{minutes}:{sec:02d}"

class Interval(NamedTuple):
    start: TimeStamp
    end: TimeStamp

class JsonFields:
    name = "Fichier en entrée"
    REQUIRED = set('interview', 'target_speaker', 'excluded_intervals', 'speech_intervals', 'interruption_counts')
    OPTIONAL = set('title', 'notes')

class Interview:
    name = "interview"
    subtype = dict
    REQUIRED = set('start', 'end')
    OPTIONAL = set()

class ExcludedIntervals:
    name = "excluded_intervals"
    subtype = dict
    REQUIRED = set('start', 'end')
    OPTIONAL = set('note')

    @classmethod
    def process_timecode(self, data, line, output: list, interview_interval: Interval):
        location = f'Element numéro {line} du champs {self.name}'
        if 'note' in data:
            is_str(data['note'], f'note de : {location}')

        start = TimeStamp(data['start'])
        end   = TimeStamp(data['end'])

        if start < interview_interval.start or end > interview_interval.end:
            raise ValueError(f"{line} : intervalle hors de la durée de l'interview")

        output.append(Interval(start=start, end=end))
    
class SpeechIntervals:
    name = "speech_intervals"
    subtype = dict
    REQUIRED = set('start', 'end', 'speaker')
    OPTIONAL = set('include', 'note')

    @classmethod
    def process_timecode(self, data, line, output: dict, interview_interval: Interval):
        location = f'Element numéro {line} du champs {self.name}'
        if 'note' in data:
            is_str(data['note'], f'note de : {location}')

        start = TimeStamp(data['start'])
        end   = TimeStamp(data['end'])

        if start < interview_interval.start or end > interview_interval.end:
            raise ValueError(f"{line} : intervalle hors de la durée de l'interview")

        is_str(data['speaker'], f'speaker de : {line}')
                                        
        if type(data.get('include', True)) is not bool:
            raise ValueError(f'{line}.include : true ou false est attendu.')
        
        if not data.get('include', True):
            return
    
        output.setdefault(data['speaker'], []).append(Interval(start=start, end=end))

class InterruptionCounts:
    name = "interruption_counts"
    subtype = dict
    REQUIRED = set('time', 'count')
    OPTIONAL = set('note')

    @classmethod
    def process_timecode(self, data, line, output: list, interview_interval: Interval):
        location = f'Element numéro {line} du champs {self.name}'
        if 'note' in data:
            is_str(data['note'], f'note de : {location}')
    
        time = TimeStamp(data['time'])
        count = data['count']

        if not interview_interval.start <= time <= interview_interval.end or type(count) is not int or count < 0:
            raise ValueError(f'{location} : horodatage hors limites ou cumul non entier positif ou nul.')
        output.append((time, count))

class Notes:
    name = "notes"
    subtype = list

def check_fields(value, field, comment=""):
    if not isinstance(value, dict):
        raise ValueError(f"{field.name} : un format JSON est attendu")
    
    missing = field.REQUIRED - value.keys()
    unknown = value.keys() - field.REQUIRED - field.OPTIONAL
    if missing:
        raise ValueError(f"{field.name} {comment} : champs manquants : {', '.join(sorted(missing))}.")
    if unknown:
        raise ValueError(f"{field.name} {comment} : champs inconnus : {', '.join(sorted(unknown))}. Vérifiez l'orthographe.")

def is_str(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} : une chaîne de caractères non vide est attendue.")


def validate_interview(data):

    # Tests des champs dans des données d'entrée
    check_fields(data, JsonFields)

    is_str(data['target_speaker'], 'target_speaker')
    if 'title' in data:
        is_str(data['title'], 'title')

    for name in ['excluded_intervals', 'speech_intervals', 'interruption_counts', 'notes']:
        if not isinstance(data.get(name, []), list):
            raise ValueError(f'{name} : une liste JSON est attendue.')

    [is_str(note, f'note numéro {index}') for index, note in enumerate(data.get('notes', []))]

    check_fields(data['interview'], Interview)
    [check_fields(element, ExcludedIntervals, comment=f'numéro {index}')  
     for index, element in enumerate(data['excluded_intervals'])]
    [check_fields(element, SpeechIntervals, comment=f'numéro {index}')
     for index, element in enumerate(data['speech_intervals'])]
    [check_fields(element, InterruptionCounts, comment=f'numéro {index}')
     for index, element in enumerate(data['interruption_counts'])]

    # Test et des timecode du format des données
    start = TimeStamp(data['interview']['start'])
    end   = TimeStamp(data['interview']['end'])
    tot_interval = Interval(start=start, end=end)

    if end <= start:
        raise ValueError('interview : la fin doit être après le début.')

    excluded = []
    checkpoints = []
    speech_by_speaker = {}
    for field, output in zip(
        (ExcludedIntervals, SpeechIntervals, InterruptionCounts), 
        (excluded, speech_by_speaker, checkpoints)):

        for index, interval in enumerate(data[field.name]):
            field.process_timecode(interval, line=index, output=output, interview_interval=tot_interval)


    for _, intervals in [(ExcludedIntervals.name, excluded), *speech_by_speaker.items()]:
        # Mettre à jour la liste d’origine.
        intervals[:] = merge_intervals(intervals)

    checkpoints.sort()
    if len(checkpoints) < 2 or checkpoints[0] != (start, 0) or checkpoints[-1][0] != end:
        raise ValueError('interruption_counts : renseigner zéro au début et le cumul total à la fin.')
    
    for previous, following in zip(checkpoints, checkpoints[1:]):
        if previous[0] == following[0] or previous[1] > following[1]:
            raise ValueError('interruption_counts : horodatages uniques et cumuls croissants ou égaux requis.')
        
    return data

def merge_intervals(intervals):
    intervals.sort()
    merged_intervals = []

    for interval in intervals:
        if merged_intervals and interval.start < merged_intervals[-1].end:
            # Fusionner avec le dernier intervalle en conservant la fin la plus grande
            previous = merged_intervals[-1]
            merged_intervals[-1] = Interval(start=previous.start, end=max(previous.end, interval.end))
        else:
            merged_intervals.append(Interval(start=previous.start, end=interval.end))

    return merged_intervals


def overlap_duration(a, b, c, d):
    return max(0, min(b, d) - max(a, c))

def segment_speaker(interview_interval, excluded):
    # Exclure le temps de parole accordé à l'invité pour lequel le temps est exclu par une pause
    segments = []
    
    cursor = interview_interval.start
    for t_start, t_end in excluded:
        if t_start >= time:
            break
        
        if cursor < t_start:
            segments.append(Interval(start=cursor, end=t_start))

        cursor = min(t_end, time)

    if cursor < time:
        segments.append(Interval(start=cursor, end=time))
    return segments

def analyze(data, timestamp=None):
    validate_interview(data)

    interview_interval = Interval(start=TimeStamp(data[Interview.name]['start']), end=TimeStamp(data[Interview.name]['end']))
    time = interview_interval.end if timestamp is None else TimeStamp(timestamp)

    if not interview_interval.start <= time <= interview_interval.end:
        raise ValueError(f'L’horodatage doit être compris entre {start.format_duration()} et {end.format_duration()}.')
    
    excluded = sorted(Interval(start=TimeStamp(item['start']), end=TimeStamp(item['end']))
                      for item in data[ExcludedIntervals.name])
    
    speech = [Interval(start=TimeStamp(item['start']), end=TimeStamp(item['end'])) 
              for item in data[SpeechIntervals.name] 
              if item['speaker'] == data['target_speaker'] and item.get('include', True)]

    segments = segment_speaker()

    effective_speech = []
    duration = 0

    for a, b in segments:
        for c, d in speech:
            x, y = max(a, c), min(b, d)
            if y > x:
                effective_speech.append((duration + x - a, duration + y - a))
        duration += b - a

    total_speech = sum(b - a for a, b in effective_speech)
    checkpoints = sorted((parse_timestamp(item['time']), item['count']) for item in data['interruption_counts'])
    previous = max(item for item in checkpoints if item[0] <= time)
    following = min(item for item in checkpoints if item[0] >= time)
    minimum, maximum = previous[1], following[1]
    minutes = []

    for a in range(0, duration, 60):
        b = min(a + 60, duration)
        speech_seconds = sum(overlap_duration(a, b, c, d) for c, d in effective_speech)
        minutes.append({
            'minute': a // 60 + 1,
            'effective_start': format_duration(a), 'effective_end': format_duration(b),
            'observed_duration_seconds': b - a, 'speech_seconds': speech_seconds,
            'speech_percentage': 100 * speech_seconds / (b - a),
        })

    warnings = list(data.get('notes', []))
    warnings.append(f'Les minutes commencent à {format_duration(start)} et excluent les interludes. La dernière peut être partielle.')
    omitted = [item for item in data['speech_intervals'] if item['speaker'] == data['target_speaker'] and not item.get('include', True) and parse_timestamp(item['start']) < time]
    
    for item in omitted:
        warnings.append(f"Parole exclue du calcul : {item['start']} – {item['end']}. {item.get('note', '')}".strip())
    
    if not speech:
        warnings.append('Aucun intervalle de parole inclus pour la personne cible. Le total décrit uniquement le relevé fourni.')
    
    if minimum != maximum:
        warnings.append('Nombre exact d’interruptions inconnu à cet instant : bornes issues des cumuls encadrants, sans interpolation.')
    
    return {
        'title': data.get('title', 'Analyse de l’interview'),
        'target_speaker': data['target_speaker'], 
        'video_timestamp': format_duration(time),
        'video_start': format_duration(start), 
        'interview_video_end': format_duration(end),
        'excluded_interlude_seconds': time - start - duration,
        'interview_duration_seconds': duration,
        'minimum_interruptions': minimum,
        'maximum_interruptions': maximum,
        'previous_checkpoint': {'timestamp': format_duration(previous[0]), 'count': minimum},
        'following_checkpoint': {'timestamp': format_duration(following[0]), 'count': maximum},
        'minimum_interruptions_per_minute': minimum * 60 / duration if duration else None,
        'maximum_interruptions_per_minute': maximum * 60 / duration if duration else None,
        'total_speech_seconds': total_speech,
        'speech_percentage': 100 * total_speech / duration if duration else None,
        'speech_by_minute': minutes, 
        'excluded_speech_count': len(omitted), 
        'warnings': warnings,
    }


def generate_html(result):
    r = result

    def format_number(n):
        return f"{n:.2f}".replace('.', ',')
    
    lower, upper = r['minimum_interruptions'], r['maximum_interruptions']
    count = str(lower) if lower == upper else f"{lower} à {upper}"
    minimum_rate = r['minimum_interruptions_per_minute']
    maximum_rate = r['maximum_interruptions_per_minute']
    rate = 'Non défini' if minimum_rate is None else (format_number(minimum_rate) if lower == upper else f"{format_number(minimum_rate)} à {format_number(maximum_rate)}")
    share = 'Non définie' if r['speech_percentage'] is None else format_number(r['speech_percentage']) + ' %'
    rows = []

    for m in r['speech_by_minute']:
        partial = ' <span class="partial">partielle</span>' if m['observed_duration_seconds'] < 60 else ''
        rows.append(f'''<tr><th scope="row">{m['minute']}{partial}</th>
<td>{m['effective_start']} – {m['effective_end']}</td>
<td><strong>{m['speech_seconds']} s</strong></td>
<td><div class="proportion"><meter min="0" max="100" value="{m['speech_percentage']:.8f}" aria-label="Part du temps de parole, minute {m['minute']}"></meter><span>{format_number(m['speech_percentage'])} %</span></div></td></tr>''')
    table = ''.join(rows) or '<tr><td colspan="4">Aucune durée écoulée à cet horodatage.</td></tr>'
    notes = ''.join(f'<li>{escape(note)}</li>' for note in r['warnings'])
    status = 'Temps de parole incomplet : des intervalles de parole sont exclus du relevé.' if r['excluded_speech_count'] > 0 else ''
    alert = f'<p class="alert">{escape(status)}</p>' if status else ''
    # Le modèle est résolu à côté du script, indépendamment du dossier de lancement.
    template_path = Path(__file__).resolve().with_name('report_template.html')
    try:
        template = Template(template_path.read_text(encoding='utf-8'))
        return template.substitute(
            title=escape(r['title']),
            video_timestamp=r['video_timestamp'],
            video_start=r['video_start'],
            excluded_interlude=format_duration(r['excluded_interlude_seconds']),
            interview_duration=format_duration(r['interview_duration_seconds']),
            total_speech=format_duration(r['total_speech_seconds']),
            rate=rate, 
            count=count, 
            share=share,
            alert=alert,
            table_rows=table, 
            notes=notes,
            previous_count=r['previous_checkpoint']['count'],
            previous_time=r['previous_checkpoint']['timestamp'],
            following_count=r['following_checkpoint']['count'],
            following_time=r['following_checkpoint']['timestamp'],
        )
    except FileNotFoundError as error:
        raise ValueError(f"Modèle HTML introuvable : {template_path}. Placez report_template.html à côté du script.") from error
    except KeyError as error:
        raise ValueError(f"Variable inconnue dans le modèle HTML : {error.args[0]}.") from error
    except ValueError as error:
        raise ValueError(f"Syntaxe invalide dans le modèle HTML : {error}") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('input_file', help="Fichier de données JSON")
    parser.add_argument('timestamp', nargs='?', help="Borne vidéo M:SS ou H:MM:SS ; par défaut, la fin de l’interview.")
    parser.add_argument('-o', '--output', nargs='?', const='rapport_interview.html', default='rapport_interview.html', metavar='FILE', help="Chemin du rapport HTML.")
    args = parser.parse_args()

    try:
        data = load_interview(args.input_file)
        result = analyze(data, args.timestamp)

        
        output_path = Path(args.output or 'rapport_interview.html').expanduser()
        if output_path.resolve() == Path(args.input_file).expanduser().resolve():
            raise ValueError("Le rapport ne doit pas écraser le fichier d’entrée.")
        output_path.write_text(generate_html(result), encoding='utf-8')
        print(f"Rapport HTML créé : {output_path.resolve()}")

    except (ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
