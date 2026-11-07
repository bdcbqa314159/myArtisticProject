# Le site sur ton Mac — mode d'emploi

Comment installer ce qu'il faut, voir le site sur ton ordinateur, et le
modifier. Aucune connaissance technique supposée.

Tu ne taperas qu'une seule ligne dans le Terminal de toute ta vie :
celle de l'étape 1. Tout le reste se fait à la souris.

---

## Ce qu'il faut comprendre d'abord, en trois phrases

Le site **est** un dossier de fichiers sur ton Mac. Les textes que tu y
changes deviennent les textes de la page, et les photographies que tu y
déposes deviennent les photographies des projets.

Il y a deux copies : **celle sur ton Mac**, où tu travailles
tranquillement, et **celle en ligne**, que tout le monde verra. Rien de
ce que tu fais sur ton Mac n'apparaît en ligne tout seul.

Tu peux donc tout essayer sans aucun risque. Si quelque chose te
déplaît, ferme sans enregistrer et recommence.

---

## Étape 1 — installer les deux outils (une seule fois)

### a. Homebrew

Homebrew sert à installer l'outil suivant, et installe au passage les
outils de développement d'Apple dont le panneau d'édition a besoin.

Ouvre **Terminal** (⌘-espace, tape `terminal`, Entrée), colle cette
ligne, Entrée, et suis ce qu'elle demande — elle demandera ton mot de
passe de session, c'est normal :

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Cela prend quelques minutes. **C'est la seule commande de tout ce
guide.** À la fin, Homebrew affiche parfois deux ou trois lignes à
coller à leur tour : colle-les.

### b. GitHub Desktop

C'est l'application qui fait l'aller-retour entre ton Mac et
l'hébergeur, sans ligne de commande.

1. va sur <https://desktop.github.com>, télécharge, installe
2. ouvre-la, **Sign in to GitHub.com**, connecte-toi
3. menu **File → Clone repository…**, onglet **URL**, colle l'adresse du
   dépôt qu'on t'a donnée, puis **Clone**

GitHub Desktop te dit où il a mis le dossier — en général
`Documents/GitHub/`. Note-le, c'est là que vit le site.

> **Et Zola ?** C'est le programme qui fabrique les pages. Tu n'as rien
> à faire : la première fois que tu lanceras l'aperçu, il proposera de
> l'installer lui-même et le fera. Compte une minute, une seule fois.

---

## Étape 2 — voir le site

Ouvre le dossier du site dans le Finder et **double-clique
`preview.command`**.

Une fenêtre noire s'ouvre — c'est normal, et elle doit rester ouverte.
Au bout de quelques secondes, deux onglets s'ouvrent dans ton
navigateur :

| | |
|---|---|
| **le site** | la page, exactement comme elle sera |
| **le studio** | la même page, avec une barre en haut pour la modifier |

> **Le panneau est en anglais pour l'instant.** Les quelques phrases
> qu'il affiche sont citées telles quelles dans ce guide, avec leur
> traduction. Le passer en français est prévu.

Si les onglets ne s'ouvrent pas tout seuls, la fenêtre noire affiche les
deux adresses : copie-les dans ton navigateur.

> L'adresse du studio change à chaque fois, exprès : elle contient un
> code à usage unique, pour qu'aucune autre page ouverte dans ton
> navigateur ne puisse atteindre tes fichiers.

**Pour tout arrêter :** reviens sur la fenêtre noire et fais
**Ctrl-C** (la touche Contrôle et la lettre C). Tu peux fermer la
fenêtre ensuite.

---

## Étape 3 — modifier la page

Tout se passe dans l'onglet **studio**, sur la page elle-même. Le bouton
**Everything as a list** en haut à droite montre la même chose sous
forme de liste — pratique pour ajouter ou supprimer un projet.

### Le texte

La barre du haut dit *« Click any text on the page to change it »* —
clique sur n'importe quel texte pour le changer.

Passe la souris sur un titre, une phrase, un bouton : il s'éclaire.
**Clique dessus et écris.** La barre affiche alors *« Enter to keep it,
Escape to leave it alone »* :

- **Entrée** pour garder
- **Échap** pour laisser comme c'était

Puis *« Saving… »*, et enfin *« Saved »* — c'est enregistré.
*« Nothing changed »* veut dire que rien n'a été modifié.

La page se reconstruit toute seule et se recharge avec ta modification.
Elle attend que le site soit vraiment reconstruit avant de se recharger,
donc une seconde ou deux peuvent passer : c'est normal.

### Les photographies

Les six emplacements de la section *Selected Work* acceptent une image.

Survole-les : ils affichent *« Drop a photograph here, or click »* s'ils
sont vides, *« Drop a new one, or click to replace »* s'ils ont déjà une
image.

- **Fais glisser** un fichier depuis le Finder directement sur
  l'emplacement, **ou clique** dessus pour choisir un fichier
- une fenêtre s'ouvre, avec l'aperçu de l'image, et la question
  *« What does it show? »*
- **écris ce qu'elle montre** — c'est obligatoire
- **Save** pour valider, **Cancel** ou Échap pour abandonner

> **Pourquoi obligatoire ?** Cette description est ce qu'on lit à voix
> haute aux personnes qui ne voient pas l'image, et ce que lisent les
> moteurs de recherche. Le moment où tu déposes une photographie est le
> seul où tu sais ce qu'elle montre. Le site refuse une image sans
> description, exprès.

JPEG, PNG ou WebP. Environ 1600 pixels sur le grand côté suffisent : le
site réduit et convertit tout seul.

Pour changer **seulement la description** d'une image déjà en place :
clique dessus et modifie le texte sans choisir de nouveau fichier.

---

## Ce qui ne peut pas casser

Le panneau refuse ce qui abîmerait le site, et te dit pourquoi :

- une photographie sans description
- un fichier qui n'est pas une image, quel que soit son nom
- un texte vide, ou plus long que la place prévue
- les caractères invisibles qui arrivent parfois avec un copier-coller
  depuis Word ou un PDF

Et il ne touche jamais aux informations **vérifiées** — les rôles, les
dates, les preuves. Celles-là se contrôlent sur pièces, pas dans un
navigateur.

Si une modification est refusée, **rien n'a été changé** : le fichier
est remis exactement comme il était.

---

## Quand ça ne marche pas

| ce que tu vois | ce que c'est |
|---|---|
| *« The site is not answering »* dans le studio | la fenêtre noire a été fermée, ou le site se reconstruit. Relance `preview.command` si besoin. Ce que tu as écrit est enregistré. |
| *« Still saving the last one »* | attends une seconde : l'enregistrement précédent n'est pas fini. |
| le studio ne s'ouvre pas, la page oui | il manque Python. La fenêtre noire te donne la ligne à coller. |
| la fenêtre noire se ferme tout de suite | le dossier a été déplacé. Retrouve-le et double-clique à nouveau. |
| une modification ne s'affiche pas | attends deux secondes, le site se reconstruit. Sinon recharge la page. |

En dernier recours, dans GitHub Desktop : **History**, clic droit sur la
dernière ligne, **Revert**. Cela annule la dernière modification sans
rien perdre d'autre.

---

## Publier — pas encore un bouton

Aujourd'hui, mettre le site en ligne passe par le studio qui l'a
construit : les modifications sont relues avant d'être publiées, et un
contrôle automatique vérifie que la page se construit toujours.

Ce n'est pas une limite technique, c'est une précaution pendant que le
contenu définitif arrive — les rôles doivent être vérifiés, les mentions
légales complétées, et le site dit explicitement aux moteurs de
recherche de l'ignorer tant que ce n'est pas fait.

**En attendant : modifie autant que tu veux sur ton Mac.** Rien ne part
en ligne tant que personne ne le publie, et tout ce que tu écris est
conservé.

Quand tu veux faire relire ce que tu as fait : ouvre GitHub Desktop, il
liste tes modifications. Préviens le studio, qui s'occupe du reste.
