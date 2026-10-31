# Analyse d’interview depuis un fichier JSON

Un outil écrit en Python pour mesurer le temps de parole, les interruptions et leur évolution pendant une interview, une réunion ou un débat. Python 3, sans dépendance supplémentaire. Le rendu HTML/CSS et les graphiques SVG ont été codés par IA.

## Méthodologie

- **Temps de parole** : sont comptabilisés les intervalles pendant lesquels le locuteur parle, sans être interrompu et sans qu’une autre personne parle par-dessus. Il s’agit de son temps d’expression sans interférence.

- **Interruptions** : sont comptabilisées les interventions qui coupent le propos de la personne interviewée de manière agressive ou insistante, en l’empêchant de terminer une idée ou de répondre à une question, ou en imposant un changement de sujet. Les brèves demandes de précision, d’environ une à deux secondes, ne sont pas comptabilisées lorsqu’elles portent directement sur le propos : demande de définition, de chiffres, de source ou de contexte.

### Pourquoi ne pas automatiser entièrement la détection des temps de parole et des interruptions ?

Une interruption peut remplir des fonctions différentes :

- **Clarifier une information** : demander brièvement la source d’un chiffre ou la définition d’un terme, puis laisser la personne poursuivre son explication.
- **Couper le propos** : commenter, poser une nouvelle question ou multiplier les interventions vocales de façon à empêcher la personne de poursuivre son raisonnement.

Un outil automatique peut repérer les changements de locuteur et les chevauchements de voix. Cela ne permet pas forcémeent de distinguer une demande de clarification d’une intervention qui coupe le propos. Cette distinction nécessite le contexte du débat.

L’analyse humaine reste à mon sens nécessaire pour appliquer ces critères. Publier les horodatages permet à chacun de réécouter les passages concernés, de vérifier le décompte et l'honnêteté du relevé.

### Mesures

- À partir d’une vidéo ou d'un podcast : utilisez les horodatages du lecteur pour relever les prises de parole et les interruptions.
- En réunion, sans enregistrement : utilisez un chronomètre et notez les horodatages dans un carnet. Cette méthode demande d'être réactif pour suivre les échanges tendus.

## Utilisation

### Arguments

```bash
python read_interview.py <input_file> [endpoint] [-o <output_file>]
```

| Argument ou option | Description |
|---|---|
| `<input_file>` | Chemin du fichier JSON contenant les données de l’interview (obligatoire). |
| `[endpoint]` | Horodatage vidéo jusqu’auquel calculer les statistiques, au format `M:SS` ou `H:MM:SS`. Facultatif : sans cette valeur, toute l’interview est analysée. |
| `-o [output_file]` | Génère le rapport HTML au chemin indiqué. Si l’option est absente ou fournie sans chemin, utilise `rapport_parloscope.html` dans le dossier courant. |

Les éléments entre `<.>` sont à remplacer par vos valeurs. Les éléments entre `[.]` sont facultatifs. Ces délimiteurs ne doivent pas être saisis.

### Exemple

Pour analyser l’interview jusqu’à l’horodatage vidéo `12:00` et enregistrer le rapport HTML :

```bash
python read_interview.py interview_francetv_marie_dupont.json 12:00 -o rapport_francetv_marie_dupont.html
```

Version simplifiée : 

```bash
python read_interview.py interview_francetv_marie_dupont.json
```
Vous trouverez le compte rendu dans `rapport_parloscope.html`

## Format JSON d’entrée

Vous pouvez trouver un exemple minimal dans interview_template.json. Ce fichier représente votre relevé d'horodotage. Si vous avez noté sur un carnet, vous pouvez reporter votre horodotage dans ce fichier.

### Description des champs du json

| Champ | Règle |
| --- | --- |
| `title` | Texte facultatif, affiché dans le rapport. |
| `interview.start`, `interview.end` | Horodatages obligatoires (format H:MM:SS) ; la fin doit être après le début. |
| `target_speaker` | Identifiant de la personne dont on mesure le temps de parole. |
| `excluded_intervals` | Liste obligatoire, éventuellement vide. Chaque entrée contient `start`, `end` et éventuellement un un commentaire `label`. Ces périodes sont retirées de la durée et des prises de parole (temps de pause). |
| `speech_intervals` | Liste obligatoire. Chaque entrée contient `speaker`, `start`, `end`, éventuellement `include` pour comptabiliser ou non ce temps et `note` pour commentaire sur ce temps. L’absence de `include` équivaut à `true`. |
| `interruption_counts` | Liste de cumuls `count` associés au dénombrement d'interruptions à un instant `time`, avec éventuellement une `note`. Ce sont les interruptions de la personne cible, comptées depuis le début de l’interview. Par exemple, sont comptées comme une interruption un changement de sujet forcé qui empêche la personne de finir son propos ou de répondre totalement à une question. Une interruption de parole peut aussi être liée à un brouhaha de personnes scandalisées qui bordélise l'interview ou le débat en cours. |
| `notes` | Liste facultative de textes libres. |

### Horodatages et intervalles

- Utiliser le format `M:SS` ou `H:MM:SS` (ce qu'il y a sur YouTube), par exemple `"12:03"` ou `"1:02:03"`. Les nombres seuls et les fractions de seconde ne sont pas acceptés.
- Tous les temps sont des positions dans la vidéo d’origine, y compris après les interludes.
- Les pauses ne doivent pas se chevaucher. 
- Les prises de parole d’une même personne ne doivent pas se chevaucher non plus.
- Les chevauchements entre personnes différentes sont autorisés.
- Un temps de parole qui traverse une pause est automatiquement découpé pour exclure la partie située dans la pause (pas de triche).
- Les périodes sans prise de parole renseignée ne sont pas attribuées à la personne cible. Un relevé incomplet donne donc un temps de parole sous-estimé.

### Cumuls d’interruptions

Renseigner obligatoirement un cumul de `0` au temps associé à `interview.start` et le total à `interview.end`. Les autres points sont facultatifs. Les horodatages doivent être uniques ; les cumuls sont des entiers positifs ou nuls en ordre croissant. Idéalement il faudrait relever tous les instants où une interruption se passe pour vérifier la comptabilité. Comme certaines interview peuvent être une purge à écouter, on peut compter les interruptions et relever leur nombre cumulé à un instant donné.


### Ligne incertaine ou incorrecte

Votre fichier conserve l’intervalle initial erroné sans le compter :

```json
{
  "speaker": "guest",
  "start": "10:58",
  "end": "10:06",
  "include": false,
  "note": "Fin à vérifier dans la vidéo."
}
```

Corrigez le champs `end`, puis passez `include` à `true` après vérification. Une ligne exclue doit garder des horodatages syntaxiquement valides, mais peut conserver une fin antérieure au début. Elle est signalée dans le rapport si son début précède l’instant analysé.
