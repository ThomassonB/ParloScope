# Analyse d’interview depuis un fichier JSON

Python 3, sans dépendance supplémentaire.

## Utilisation

### Arguments

```bash
python analyse_interview.py <input_file> [timestamp] -o [output_file]
```

| Argument ou option | Description |
|---|---|
| `<input_file>` | Chemin du fichier JSON contenant les données de l’interview (obligatoire). |
| `[timestamp]` | Horodatage vidéo jusqu’auquel calculer les statistiques, au format `M:SS` ou `H:MM:SS`. Facultatif : sans cette valeur, toute l’interview est analysée. |
| `-o [output_file]`, `--output [output_file]` | Génère le rapport HTML au chemin indiqué. Si l’option est absente ou fournie sans chemin, utilise `rapport_interview.html` dans le dossier courant. |

Les éléments entre `<.>` sont à remplacer par vos valeurs. Les éléments entre `[.]` sont facultatifs. Ces délimiteurs ne doivent pas être saisis.

Les options `--html`, `--json` et `--text` sont mutuellement exclusives. Par défaut, le script génère un `html`.

### Exemple

Pour analyser l’interview jusqu’à l’horodatage vidéo `12:00` et enregistrer le rapport HTML :

```bash
python analyse_interview.py interview_francetv_marie_dupont.json 12:00 --html rapport_francetv_marie_dupont.html
```

## Format JSON d’entrée

Vous pouvez trouver un exemple minimal dans interview_template.json.

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

Renseigner obligatoirement un cumul de `0` àau temps associé à `interview.start` et le total à `interview.end`. Les autres points sont facultatifs. Les horodatages doivent être uniques ; les cumuls sont des entiers positifs ou nuls et ne peuvent pas diminuer. Idéalement il faudrait relever tous les instants où une interruption se passe pour vérifier la comptabilité. Comme certaines interview peuvent être une purge à écouter, on peut compter les interruptions et relever leur nombre cumulé à un instant donné.


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

Corrigez `end`, puis passez `include` à `true` après vérification. Une ligne exclue doit garder des horodatages syntaxiquement valides, mais peut conserver une fin antérieure au début. Elle est signalée dans le rapport si son début précède l’instant analysé.
