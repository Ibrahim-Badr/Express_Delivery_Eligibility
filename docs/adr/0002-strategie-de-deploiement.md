# ADR 0002 : Stratégie de déploiement et gestion des environnements

## Contexte
L'application doit évoluer à travers trois environnements distincts : Dev, Test, et Prod. Il faut une stratégie robuste pour provisionner l'infrastructure et déployer le code de manière automatisée, sans intervention manuelle risquée.

## Décision
Nous adopterons l'approche **Infrastructure as Code (IaC)** combinée à l'**Intégration et Déploiement Continus (CI/CD)** :
1. **Infrastructure (IaC)** : Utilisation de **Terraform**. Cela permet de créer, modifier et détruire (pour économiser le budget) les ressources Azure avec une simple commande.
2. **CI/CD** : Utilisation de **GitHub Actions**. Les workflows automatiseront les tests (Pytest) et le déploiement.
3. **Stratégie de branches** :
   * La branche `develop` déploiera sur l'environnement de **Dev**.
   * La branche `release` déploiera sur l'environnement de **Test**.
   * La branche `main` déploiera sur l'environnement de **Prod**.

## Conséquences
* **Positives** : 
  * Environnements 100% reproductibles.
  * Déploiements fiables et automatisés.
  * Protection du budget étudiant grâce à la facilité de destruction de l'infrastructure (`terraform destroy`).
* **Négatives** : 
  * Courbe d'apprentissage initiale pour configurer Terraform et GitHub Actions.
