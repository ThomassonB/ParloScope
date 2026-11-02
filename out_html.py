from html import escape
from string import Template
from pathlib import Path

from interview_charts import render_charts
from read_interview import Interval

def generate_html(result):

    def format_number(n):
        return f"{n:.2f}".replace('.', ',')
    
    effective_duration = result.no_break_duration()

    if not result.disruptions:
        disruption_rate = 'Non défini'
    disruption_rate = result.disruptions[-1].count / effective_duration.time * 60

    if not result.speaker_time:
        percentage_speech = 'Non définie'

    percentage_speech = 100 * sum(speech.duration() for speech in result.speaker_time).time / effective_duration.time
    
    rows = []
    for minute in result.get_statistics_by_minutes():
        partial = f' <span class="partial">(durée : {minute["interval"].duration().time}s)</span>' if minute['interval'].duration().time < 60 else ''
        rows.append(
            f'''
            <tr>
            <th scope="row">{minute['interval'].start.time // 60 + 1}{partial}</th>
            <td><strong>{minute['speech_time'].time} s</strong></td>
            <td>
            <div class="proportion">
                <meter min="0" max="100" value="{minute['speech_percentage']:.8f}" aria-label="Part du temps de parole"></meter>
                <span>{format_number(minute['speech_percentage'])} %</span>
            </div></td></tr>
            ''')
        
    table = ''.join(rows)
    #notes = ''.join(f'<li>{escape(note)}</li>' for note in result.warnings)
    template_path = (
                    Path(__file__).resolve().parent
                    / "rapport_modele.html"
                )

    template = Template(template_path.read_text(encoding='utf-8'))

    return template.substitute(
        title=escape(result.title),
        end=result.duration.end.format(),
        start=result.duration.start.format(),
        break_time=Interval.sum(result.breaks).format(),
        interview_duration=effective_duration.format(),
        disruption_rate=format_number(disruption_rate),
        count=result.disruptions[-1].count,
        total_speech=Interval.sum(result.speaker_time).format(),
        percentage_speech=format_number(percentage_speech),
        table_rows=table, 
        #notes=notes,
        charts=render_charts(result),
    )