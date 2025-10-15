pipeline {
    agent any
    
    environment {
        PYTHON_VERSION = '3.9'
        APP_PORT = '5000'
    }
    
    stages {
        stage('Checkout') {
            steps {
                echo ' Récupération du code source...'
                checkout scm
            }
        }
        
        stage('Setup Python Environment') {
            steps {
                echo ' Configuration de l\'environnement Python...'
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }
        
        stage('Unit Tests') {
            steps {
                echo ' Exécution des tests unitaires...'
                sh '''
                    . venv/bin/activate
                    pytest test_app.py -v --cov=app --cov-report=xml --cov-report=html
                '''
            }
        }
    }
    
    post {
        always {
            echo ' Nettoyage...'
            sh '''
                rm -rf venv
            '''
        }
        
        success {
            echo ' Pipeline réussi !'
        }
        
        failure {
            echo ' Pipeline échoué !'
        }
    }
}