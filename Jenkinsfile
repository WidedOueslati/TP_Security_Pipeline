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
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Static Code Analysis (SAST)') {
            steps {
                echo 'Analyse de sécurité avec Bandit...'
                sh '''
                    . venv/bin/activate
                    bandit -r . || true
                '''
            }
        }

        stage('Run Tests') {
            steps {
                echo 'Exécution des tests unitaires...'
                sh '''
                    . venv/bin/activate
                    pytest --maxfail=1 --disable-warnings -q || true
                '''
            }
        }


        stage('Build Artifact') {
            steps {
                echo 'Construction du build...'
                sh '''
                    . venv/bin/activate
                    python -m zipfile -c build.zip app.py requirements.txt tests
                '''
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
