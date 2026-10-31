#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path
from typing import NamedTuple

def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Champs JSON répété : {key}.")
        result[key] = value
    return result


def load_interview(path, endpoint=None):
    """Charge les données UTF-8 ; refuse les clés répétées et les JSON mal formés."""
    try:
        with open(Path(path).expanduser(), encoding="utf-8") as file:
            data = json.load(file, object_pairs_hook=reject_duplicate_keys)

    except json.JSONDecodeError as error:
        raise ValueError(f"JSON invalide, ligne {error.lineno}, colonne {error.colno} : {error.msg}") from error
    
    return validate_interview(data, endpoint)

class TimeStamp:
    time: int

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

    @classmethod
    def from_seconds(cls, seconds) -> 'TimeStamp':
        if type(seconds) is not int or seconds < 0:
            raise ValueError('Le temps doit être un entier positif ou nul en secondes.')
        
        instance = object.__new__(cls)
        object.__setattr__(instance, 'time', seconds)
        object.__setattr__(instance, 'text', instance.format_duration())
        return instance

    def __sub__(self, other):
        if not isinstance(other, TimeStamp):
            return NotImplemented
        return TimeStamp.from_seconds(self.time - other.time)

    def __add__(self, other):
        if not isinstance(other, TimeStamp):
            return NotImplemented
        return TimeStamp.from_seconds(self.time + other.time)

    def __lt__(self, other):
        if not isinstance(other, TimeStamp):
            return NotImplemented
        return self.time < other.time

    def __gt__(self, other):
        if not isinstance(other, TimeStamp):
            return NotImplemented
        return self.time > other.time

    def __le__(self, other):
        if not isinstance(other, TimeStamp):
            return NotImplemented
        return self.time <= other.time
    
    def __ge__(self, other):
        if not isinstance(other, TimeStamp):
            return NotImplemented
        return self.time >= other.time
        
    def format_duration(self):
        hours, remainder = divmod(self.time, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}:{minutes:02d}:{seconds:02d}"

class Interval(NamedTuple):
    start: TimeStamp
    end: TimeStamp

    def duration(self) -> TimeStamp:
        return self.end - self.start

    def intersection(self, other):
        if not isinstance(other, Interval):
            return NotImplemented
        start, end = max(self.start, other.start), min(self.end, other.end)
        return Interval(start, end) if start < end else None

class InterruptionCheckpoint(NamedTuple):
    time: TimeStamp
    count: int

class JsonFields:
    name = "Fichier en entrée"
    REQUIRED = set(('interview', 'target_speaker', 'excluded_intervals', 'speech_intervals', 'interruption_counts',))
    OPTIONAL = set(('title', 'notes',))

class Interview:
    name = "interview"
    subtype = dict
    REQUIRED = set(('start', 'end',))
    OPTIONAL = set()

class ExcludedIntervals:
    name = "excluded_intervals"
    subtype = dict
    REQUIRED = set(('start', 'end',))
    OPTIONAL = set(('note',))

    @classmethod
    def check_timecode(self, data, interview_interval: Interval):
        for line, interval in enumerate(data[self.name]):
            location = f'Element numéro {line} du champs {self.name}'

            if 'note' in interval:
                is_str(interval['note'], f'note de : {location}')

            start = TimeStamp(interval['start'])
            end   = TimeStamp(interval['end'])

            if start < interview_interval.start or end > interview_interval.end:
                raise ValueError(f"{line} : intervalle hors de la durée de l'interview")
        
class SpeechIntervals:
    name = "speech_intervals"
    subtype = dict
    REQUIRED = set(('start', 'end', 'speaker',))
    OPTIONAL = set(('include', 'note',))

    @classmethod
    def check_timecode(self, data, interview_interval: Interval):
        for line, interval in enumerate(data[self.name]):
            location = f'Element numéro {line} du champs {self.name}'
            if 'note' in interval:
                is_str(interval['note'], f'note de : {location}')

            start = TimeStamp(interval['start'])
            end   = TimeStamp(interval['end'])

            if start < interview_interval.start or end > interview_interval.end:
                raise ValueError(f"{line} : intervalle hors de la durée de l'interview")

            is_str(interval['speaker'], f'speaker de : {line}')
                                            
            if type(interval.get('include', True)) is not bool:
                raise ValueError(f'{line}.include : true ou false est attendu.')

class InterruptionCounts:
    name = "interruption_counts"
    subtype = dict
    REQUIRED = set(('time', 'count',))
    OPTIONAL = set(('note',))

    @classmethod
    def check_timecode(self, data, interview_interval: Interval):

        checkpoints = []
        for line, interval in enumerate(data[self.name]):
            location = f'Element numéro {line} du champs {self.name}'
            if 'note' in interval:
                is_str(interval['note'], f'note de : {location}')
        
            time = TimeStamp(interval['time'])
            count = interval['count']

            if not interview_interval.start <= time <= interview_interval.end or type(count) is not int or count < 0:
                raise ValueError(f'{location} : horodatage hors limites ou cumul non entier positif ou nul.')
            checkpoints.append((time.time, count))

        checkpoints.sort()
        if len(checkpoints) < 2 or checkpoints[0] != (interview_interval.start.time, 0) or checkpoints[-1][0] != interview_interval.end.time:
            raise ValueError('interruption_counts : renseigner zéro au début et le cumul total à la fin.')
        
        for previous, following in zip(checkpoints, checkpoints[1:]):
            if previous[0] == following[0] or previous[1] > following[1]:
                raise ValueError('interruption_counts : horodatages uniques et cumuls croissants ou égaux requis.')

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


def validate_interview(data, endpoint=None):

    # Tests des champs dans des données d'entrée
    check_fields(data, JsonFields)

    is_str(data['target_speaker'], 'target_speaker')
    if 'title' in data:
        is_str(data['title'], 'title')

    for name in ['excluded_intervals', 'speech_intervals', 'interruption_counts', 'notes']:
        if not isinstance(data.get(name, []), list):
            raise ValueError(f'{name} : une liste JSON est attendue.')

    [is_str(note, f'note numéro {index}') for index, note in enumerate(data.get('notes', []))]

    check_fields(data[Interview.name], Interview)
    [check_fields(element, ExcludedIntervals, comment=f'numéro {index}')  
     for index, element in enumerate(data[ExcludedIntervals.name])]
    [check_fields(element, SpeechIntervals, comment=f'numéro {index}')
     for index, element in enumerate(data[SpeechIntervals.name])]
    [check_fields(element, InterruptionCounts, comment=f'numéro {index}')
     for index, element in enumerate(data[InterruptionCounts.name])]

    # Test et des timecode du format des données
    start = TimeStamp(data[Interview.name]['start'])
    end = TimeStamp(data[Interview.name]['end']) if endpoint is None else TimeStamp(endpoint)
    interview_interval = Interval(start=start, end=end)

    if interview_interval.duration().time <= 0:
        raise ValueError('interview : la fin doit être après le début.')

    for field in (ExcludedIntervals, SpeechIntervals, InterruptionCounts):
        field.check_timecode(data, interview_interval=interview_interval)
        
    return data

def main():
    from analyse import analyze
    from out_html import generate_html

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('input_file', help="Fichier de données JSON")
    parser.add_argument('timestamp', nargs='?', help="Borne vidéo M:SS ou H:MM:SS ; par défaut, la fin de l’interview.")
    parser.add_argument('-o', '--output', nargs='?', const='rapport_interview.html', default='rapport_interview.html', metavar='FILE', help="Chemin du rapport HTML.")
    args = parser.parse_args()

    try:
        data = load_interview(args.input_file, args.timestamp)
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
