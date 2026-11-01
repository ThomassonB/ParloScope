from html import escape
from math import ceil

from read_interview import TimeStamp

WIDTH, HEIGHT = 960, 300
LEFT, RIGHT, TOP, BOTTOM = 65, 30, 36, 64
PLOT_WIDTH = WIDTH - LEFT - RIGHT
PLOT_HEIGHT = HEIGHT - TOP - BOTTOM

def text(x, y, label, anchor='middle', color='#52677e'):
    return f'''
        <text x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}" fill="{color}" font-size="13">
        {escape(str(label))}
        </text>'''


def svg_start(title, description):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{escape(title, quote=True)}" style="font-family:Arial,sans-serif">',
        f'<title>{escape(title)}</title><desc>{escape(description)}</desc>',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="white"/>',
    ]


def time_axis(parts, duration):
    span = duration.duration().time

    def x(time):
        return LEFT + (time - duration.start.time) / max(span, 1) * PLOT_WIDTH
    
    # Choisir des graduations régulières
    step = next((step for step in [1, 5, 10, 15, 30, 60, 120, 300, 600, 1800, 3600] 
                 if span / step <= 8), max(1, ceil(span / 8 / 3600) * 3600))
    
    ticks = [duration.start.time]
    ticks.extend(range((duration.start.time // step + 1) * step, duration.end.time + 1, step))

    if ticks[-1] != duration.end.time:
        if len(ticks) > 1 and duration.end.time - ticks[-1] < step * 0.45:
            ticks.pop()
        ticks.append(duration.end.time)

    for tick in ticks:
        position = x(tick)
        parts.append(
            f'''
            <line x1="{position:.2f}" y1="{TOP}" x2="{position:.2f}" y2="{TOP + PLOT_HEIGHT}" stroke="#e8edf3"/>
            ''')

        timestamp = TimeStamp.from_seconds(tick).format()
        parts.append(text(position, HEIGHT - BOTTOM + 24, timestamp))

    parts.append(text(LEFT + PLOT_WIDTH / 2, HEIGHT - 13, 'Horodatage vidéo (min:s)'))
    return x


def y_axis(parts, maximum, ticks, label):

    def y(value):
        return TOP + PLOT_HEIGHT * (1 - value / maximum)
    
    for tick in ticks:
        position = y(tick)
        parts.append(
            f'''
            <line x1="{LEFT}" y1="{position:.2f}" x2="{WIDTH - RIGHT}" y2="{position:.2f}" stroke="#e0e7ef"/>
            ''')
        parts.append(text(LEFT - 12, position + 5, tick, 'end'))
    parts.append(text(LEFT, 18, label, 'start'))
    return y


def excluded_shading(parts, segments, x):
    for interval in segments:
        position = x(interval.start.time)
        width = x(interval.end.time) - position

        parts.append(
            f'''
            <rect x="{position:.2f}" y="{TOP}" width="{width:.2f}" height="{PLOT_HEIGHT}" fill="#cbd5e1" opacity=".45">
            <title>Interlude exclu : {interval.start.format()} – {interval.end.format()}</title>
            </rect>
            ''')


def speech_chart(result):
    title = "Temps de parole"
    description = "La personne parle [1] ou ne parle pas [0]."

    parts = svg_start(title, description)

    x = time_axis(parts, result.duration)
    y = y_axis(parts, 1, [0, 1], "")


    path = [
        f'M {x(result.duration.start.time)} {y(0)}'
    ]

    excluded_shading(parts, result.breaks, x)
    for interval in result.speaker_time:
        path.extend([
            f'H {x(interval.start.time)}',
            f'V {y(1)}',
            f'H {x(interval.end.time)}',
            f'V {y(0)}',
        ])

    path.append(f'H {x(result.duration.end.time)}')

    parts.append(
        f'<path d="{" ".join(path)}" '
        'fill="none" stroke="#237d79" stroke-width="2"/>'
    )
    parts.append("</svg>")
    return title, description, ''.join(parts)

def interruptions_chart(result):
    title = 'Cumul des interruptions aux instants relevés'
    description = ''

    parts = svg_start(title, description)
    
    points = [disruption for disruption in result.disruptions]

    maximum = max([item.count for item in points] + [1])
    tick_step = max(1, ceil(maximum / 5))
    ceiling = ceil(maximum / tick_step) * tick_step

    x = time_axis(parts, result.duration)
    y = y_axis(parts, ceiling, range(0, ceiling + 1, tick_step), 'Interruptions cumulées')

    excluded_shading(parts, result.breaks, x)

    for index, point in enumerate(points):
        px, py = x(point.time.time), y(point.count)
        parts.append(
            f'''
            <circle cx="{px:.2f}" cy="{py:.2f}" r="5" fill="#405c94" stroke="white" stroke-width="1">
            <title>{point.time.format()} : {point.count} interruptions</title>
            </circle>''')
        
        # Décaler les deux derniers libellés lorsque leurs points sont proches.
        anchor = 'end' if index + 1 < len(points) and x(points[index + 1].time.time) - px < 40 else 'start'
        parts.append(text(px + (-8 if anchor == 'end' else 8), py - 10, point.count, anchor, '#314c80'))
    
    parts.append('</svg>')
    return title, description, ''.join(parts)


def histogram_bins(durations):
    """Classes de largeur constante ; borne gauche incluse, borne droite exclue."""
    if not durations:
        return []
    maximum = max(durations)
    width = next((width for width in [1, 2, 5, 10, 15, 30, 60, 120, 300, 600] 
                  if maximum // width + 1 <= 12), max(1, ceil(maximum / 10)))
    counts = [0] * (maximum // width + 1)
    for duration in durations:
        counts[duration // width] += 1
    return [{'start': index * width, 'end': (index + 1) * width, 'count': count} for index, count in enumerate(counts)]


def distribution_chart(result):
    title = 'Distribution des durées de prise de parole'
    durations = [interval.duration().time for interval in result.speaker_time]

    bins = histogram_bins(durations)
    description = f'{len(durations)} intervalles de parole au total.'
    parts = svg_start(title, description)
    maximum = max([item['count'] for item in bins] + [1])
    step = max(1, ceil(maximum / 5))
    ceiling = ceil(maximum / step) * step
    y = y_axis(parts, ceiling, range(0, ceiling + 1, step), 'Nombre d’intervalles')
    if not bins:
        parts.append(text(WIDTH / 2, HEIGHT / 2, 'Aucun intervalle de parole à afficher.'))
    for index, item in enumerate(bins):
        cell_width = PLOT_WIDTH / len(bins)
        px = LEFT + index * cell_width
        height = TOP + PLOT_HEIGHT - y(item['count'])
        label = f'{item["start"]}–{item["end"]}'
        parts.append(f'<rect x="{px + 2:.2f}" y="{y(item["count"]):.2f}" width="{cell_width - 4:.2f}" height="{height:.2f}" fill="#237d79"><title>De {item["start"]} s inclus à {item["end"]} s exclu : {item["count"]} intervalles</title></rect>')
        parts.append(text(px + cell_width / 2, HEIGHT - BOTTOM + 24, label))
        if item['count']:
            parts.append(text(px + cell_width / 2, y(item['count']) - 8, item['count']))
    parts.append(text(LEFT + PLOT_WIDTH / 2, HEIGHT - 13, 'Durée d’un intervalle de parole (secondes)'))
    parts.append('</svg>')
    return title, description, ''.join(parts)


def render_charts(result):
    speaker_time = speech_chart(result)
    disruptions = interruptions_chart(result)
    distribution = distribution_chart(result)

    plots = [speaker_time, disruptions, distribution]

    cards = []
    for title, description, svg in plots:

        cards.append(
            f'''
            <section class="chart-card">
            <h2>{escape(title)}</h2>
            <p class="chart-description">{escape(description)}</p>
            <div class="chart-scroll">{svg}</div>
            </section>
            ''')
   
    return '\n'.join(cards)
