# ADR 0003 : Sécurisation des entrées/sorties et de l'accès aux données

## Contexte
L'API REST va recevoir des requêtes externes pour évaluer l'éligibilité des commandes et devra se connecter à une base de données distante (PostgreSQL sur Azure). Il est crucial de prévenir les injections, de garantir l'intégrité des données entrantes, et de protéger les identifiants d'accès.

## Décision
Nous appliquerons le principe de défense en profondeur :

**1. Sécurisation des Entrées et Sorties**
* Utilisation du framework **FastAPI** couplé à **Pydantic**.
* Chaque requête (JSON) est strictement validée par les schémas Pydantic (ex: `OrderFeatures`). Si un type est incorrect ou qu'une valeur est hors limites (ex: `carrier_capacity` > 1.0), l'API rejette la requête (Erreur 422 Unprocessable Entity) avant même d'atteindre la logique métier ou le modèle ML.

**2. Sécurisation de l'accès à la donnée**
* **Aucun secret dans le code** : Les chaînes de connexion (URL de la base de données PostgreSQL, mots de passe) ne seront jamais versionnées dans Git.
* Utilisation d'**Azure Key Vault** : Les identifiants seront stockés de manière sécurisée dans un coffre-fort numérique sur Azure.
* L'application (via ses variables d'environnement injectées par GitHub Actions ou récupérées au runtime) lira ces secrets dynamiquement.

## Conséquences
* **Positives** : 
  * L'API est immunisée contre de nombreuses failles courantes grâce à la validation stricte.
  * Les risques de fuite de mots de passe sur GitHub sont éliminés.
* **Négatives** : 
  * Complexité légèrement accrue pour configurer l'accès entre la VM, GitHub Actions et Azure Key Vault (gestion des identités gérées - Managed Identities).
