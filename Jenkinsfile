pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                echo 'Clonage du dépôt...'
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                echo 'Installation des dépendances...'
                sh 'pip install -r requirements.txt'
            }
        }

        stage('Static Code Analysis (SAST)') {
            steps {
                echo 'Analyse de sécurité avec Bandit...'
                sh 'bandit -r . || true' 
                
            }
        }

        stage('Run Tests') {
            steps {
                echo 'Exécution des tests unitaires...'
                sh 'pytest --maxfail=1 --disable-warnings -q'
            }
        }

        stage('Build Artifact') {
            steps {
                echo 'Construction du build...'
                sh 'zip -r build.zip app.py requirements.txt tests'
            }
        }

        stage('Deploy (Simulation)') {
            steps {
                echo 'Déploiement simulé...'
                sh 'echo "Déploiement réussi (simulation) !"'
            }
        }
    }

    post {
        always {
            echo 'Pipeline terminé — nettoyage...'
            cleanWs()
        }
    }
}
