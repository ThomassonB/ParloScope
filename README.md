# Analyse d’interview depuis un fichier JSON

Un outil Python pour visualiser le temps de parole, les interruptions et leur évolution pendant une interview, une réunion ou un débat. Python 3, sans dépendance supplémentaire. Le rendu CSS et les graphiques SVG ont été codés par IA parce que j'ai autre chose à faire de ma vie.

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
python read_interview.py <input_file>
```

| Argument ou option | Description |
|---|---|
| `<input_file>` | Chemin du fichier JSON contenant les données de l’interview (obligatoire). |

Les éléments entre `<.>` sont à remplacer par vos valeurs. Ces délimiteurs ne doivent pas être saisis. Le rapport est créé dans le dossier `rendu`, son nom est le même que le fichier `.json` en entrée.

### Exemple

Dans le répertoire du script : 

```bash
python read_interview.py vos_donnees.json
```
Vous trouverez le compte rendu dans `rendu/vos_donnees.html`.

## Format JSON d’entrée

Vous pouvez trouver un exemple minimal dans `rendu/interview_template.json`. Ce fichier représente votre relevé d'horodotage. Si vous avez noté sur un carnet, vous pouvez reporter votre horodotage dans ce fichier.

### Description des champs du json

| Champ | Règle |
| --- | --- |
| `title` | Texte facultatif, affiché dans le rapport. |
| `interview.start`, `interview.end` | Horodatages obligatoires (format H:MM:SS) ; la fin doit être après le début. |
| `target_speaker` | Identifiant de la personne dont on mesure le temps de parole. |
| `excluded_intervals` | Liste obligatoire, éventuellement vide. Chaque entrée contient `start`, `end` et éventuellement un un commentaire `label`. Ces périodes sont retirées de la durée et des prises de parole (temps de pause). |
| `speech_intervals` | Liste obligatoire. Chaque entrée contient `speaker`, `start`, `end` et `note` pour un commentaire sur ce temps. |
| `interruption_counts` | Liste de cumuls `count` associés au dénombrement d'interruptions à un instant `time`, avec éventuellement une `note`. Ce sont les interruptions de la personne cible, comptées depuis le début de l’interview. Par exemple, sont comptées comme une interruption un changement de sujet forcé qui empêche la personne de finir son propos ou de répondre totalement à une question. Une interruption de parole peut aussi être liée à un brouhaha de personnes scandalisées qui bordélise l'interview ou le débat en cours. |
| `notes` | Liste facultative de textes libres. |

### Horodatages et intervalles

- Utiliser le format `M:SS` ou `H:MM:SS` (ce qu'il y a sur YouTube), par exemple `"12:03"` ou `"1:02:03"`. Les nombres seuls et les fractions de seconde ne sont pas acceptés.
- Les chevauchements entre temps de parole ne sont pas comptées double.
- Un temps de parole qui traverse une pause est automatiquement découpé pour exclure la partie située dans la pause (pas de triche).

### Cumuls d’interruptions

Les horodatages doivent être uniques ; les cumuls sont des entiers positifs ou nuls en ordre croissant. Idéalement il faudrait relever tous les instants où une interruption se passe pour vérifier la comptabilité. Comme certaines interview peuvent être une purge à écouter, on peut compter les interruptions et relever leur nombre cumulé à un instant donné.
