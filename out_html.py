from html import escape
from string import Template
from pathlib import Path

from interview_charts import render_charts

def generate_html(result):

    def format_number(n):
        return f"{n:.2f}".replace('.', ',')
    
    lower, upper = result['minimum_interruptions'], result['maximum_interruptions']
    count = str(lower) if lower == upper else f"{lower} à {upper}"
    minimum_rate = result['minimum_interruptions_per_minute']
    maximum_rate = result['maximum_interruptions_per_minute']
    rate = 'Non défini' if minimum_rate is None else (format_number(minimum_rate) if lower == upper else f"{format_number(minimum_rate)} à {format_number(maximum_rate)}")
    share = 'Non définie' if result['speech_percentage'] is None else format_number(result['speech_percentage']) + ' %'
    rows = []

    for m in result['speech_by_minute']:
        partial = ' <span class="partial">partielle</span>' if m['observed_duration_seconds'] < 60 else ''
        # <td>{m['effective_start']} – {m['effective_end']}</td>
        rows.append(
            f'''
            <tr>
            <th scope="row">{m['minute']}{partial}</th>
            <td><strong>{m['speech_seconds']} s</strong></td>
            <td>
            <div class="proportion">
                <meter min="0" max="100" value="{m['speech_percentage']:.8f}" aria-label="Part du temps de parole, minute {m['minute']}"></meter>
                <span>{format_number(m['speech_percentage'])} %</span>
            </div></td></tr>
            ''')
        
    table = ''.join(rows) or '<tr><td colspan="4">Aucune durée écoulée à cet horodatage.</td></tr>'
    notes = ''.join(f'<li>{escape(note)}</li>' for note in result['warnings'])
    status = 'Temps de parole incomplet : des intervalles de parole sont exclus du relevé.' if result['excluded_speech_count'] > 0 else ''
    alert = f'<p class="alert">{escape(status)}</p>' if status else ''

    template_path = Path(__file__).resolve().with_name('report_template.html')

    try:
        template = Template(template_path.read_text(encoding='utf-8'))
        return template.substitute(
            title=escape(result['title']),
            video_timestamp=result['video_timestamp'],
            video_start=result['video_start'],
            excluded_interlude=result['excluded_interlude'],
            interview_duration=result['interview_duration'],
            total_speech=result['total_speech_seconds'],
            rate=rate, 
            count=count, 
            share=share,
            alert=alert,
            table_rows=table, 
            notes=notes,
            charts=render_charts(result),
            previous_count=result['previous_checkpoint']['count'],
            previous_time=result['previous_checkpoint']['timestamp'],
            following_count=result['following_checkpoint']['count'],
            following_time=result['following_checkpoint']['timestamp'],
        )
    
    except FileNotFoundError as error:
        raise ValueError(f"Modèle HTML introuvable : {template_path}. Placez report_template.html à côté du script.") from error
    except KeyError as error:
        raise ValueError(f"Variable inconnue dans le modèle HTML : {error.args[0]}.") from error
    except ValueError as error:
        raise ValueError(f"Syntaxe invalide dans le modèle HTML : {error}") from error