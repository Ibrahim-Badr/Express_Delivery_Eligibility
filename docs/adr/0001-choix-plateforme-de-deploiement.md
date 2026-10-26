# ADR 0001 : Choix de la plateforme de déploiement

## Contexte
L'application d'éligibilité à la livraison express doit être mise en production. Il est nécessaire de choisir entre un hébergement On-Premise, Local, ou Cloud. 
Nous disposons d'un budget étudiant strict sur Microsoft Azure (88 $) mais avec un accès à plusieurs services gratuits pendant 12 mois (notamment 750 heures/mois pour une VM Linux et 750 heures/mois pour Azure Database for PostgreSQL).

## Décision
Nous avons décidé de déployer l'application sur le **Cloud (Microsoft Azure)**, en utilisant une architecture hybride IaaS / PaaS :
1. **Compute (IaaS)** : Une machine virtuelle **Azure Linux VM (B2ats v2)**. Elle hébergera l'application FastAPI conteneurisée avec Docker.
2. **Base de données (PaaS)** : **Azure Database for PostgreSQL (Flexible Server)**. Plutôt que de gérer la base de données nous-mêmes dans la VM, nous déléguons sa gestion (sauvegardes, haute disponibilité) à Azure, profitant de l'instance B1MS gratuite.

## Conséquences
* **Positives** : 
  * Coût nul (0 $) grâce à l'utilisation optimale des quotas gratuits étudiants.
  * Architecture professionnelle et évolutive (Cloud-native).
  * Séparation claire entre le calcul (VM) et le stockage (PaaS).
* **Négatives** : 
  * Nécessite une gestion rigoureuse (via Terraform) pour allumer/éteindre les ressources et éviter les dépassements de forfait.
