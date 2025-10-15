pipeline {
    agent any

    environment {
        PYTHON_VERSION = '3.9'
        APP_PORT = '5000'
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Récupération du code source...'
                checkout scm
            }
        }

        stage('Setup Python Environment') {
            steps {
                echo 'Configuration de l\'environnement Python...'
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    pip install bandit
                '''
            }
        }

        stage('Unit Tests') {
            steps {
                echo 'Exécution des tests unitaires...'
                sh '''
                    . venv/bin/activate
                    pytest test_app.py -v --cov=app --cov-report=xml --cov-report=html
                '''
            }
        }

        stage('SAST Scan (Bandit)') {
            steps {
                echo 'Analyse SAST avec Bandit...'
                sh '''
                    . venv/bin/activate
                    bandit -r app -f json -o bandit-report.json || true
                '''
            }
        }

        stage('SCA Scan (Dependency-Check)') {
            steps {
                echo 'Analyse SCA avec OWASP Dependency-Check...'
                sh '''
                    dependency-check.sh --project "FlaskApp" --scan . --format "HTML" --out dependency-check-report.html || true
                '''
            }
        }

        stage('Security Validation') {
            steps {
                echo 'Validation des résultats de sécurité...'
                sh '''
                    # Vérification de la sortie Bandit pour vulnérabilités élevées
                    CRITICALS=$(grep -c '"issue_severity": "HIGH"' bandit-report.json || true)
                    if [ "$CRITICALS" -gt 0 ]; then
                        echo " Vulnérabilités critiques détectées par Bandit."
                        exit 1
                    fi

                    # Vérification que le rapport Dependency-Check ne contient pas de vulnérabilités critiques
                    if grep -q "CRITICAL" dependency-check-report.html; then
                        echo " Vulnérabilités critiques détectées par Dependency-Check."
                        exit 1
                    fi

                    echo " Aucun problème critique détecté."
                '''
            }
        }
    }

    post {
        always {
            echo 'Nettoyage...'
            sh 'rm -rf venv'
        }
        success {
            echo 'Pipeline réussi (tests + sécurité OK) !'
        }
        failure {
            echo 'Pipeline échoué à cause des vulnérabilités ou tests !'
        }
    }
}
