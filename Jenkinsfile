pipeline {
    agent any

    environment {
        PYTHON_VERSION = '3.9'
        APP_PORT = '5000'
        SNYK_TOKEN = credentials('SNYK_TOKEN')
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Récupération du code source...'
                checkout scm
            }
        }

        stage('Setup Python Environment & Tools') {
            steps {
                echo 'Configuration de l\'environnement Python et installation outils (bandit, snyk, jq)...'
                sh '''
                    set -e
                    python3 -m venv venv
                    . venv/bin/activate
                    
                    snyk auth $SNYK_TOKEN
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    pip install bandit     # installe Bandit 
                    # vérifie jq (si absent, tenter d'installer via apt-get si possible)
                    if ! command -v jq >/dev/null 2>&1; then
                        echo "jq non trouvé - tentative d'installation (si l'agent le permet)..."
                        if [ -f /etc/debian_version ]; then
                            sudo apt-get update && sudo apt-get install -y jq || true
                        fi
                    fi
                    echo "Outils installés : $(bandit --version 2>/dev/null || echo 'bandit?') / $(snyk check --version 2>/dev/null || echo 'snyk?') / jq: $(jq --version 2>/dev/null || echo 'jq?')"
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
                echo 'Lancement Bandit (génère bandit-report.json)...'
                sh '''
                    set +e           # important : ne pas faire échouer immédiatement la step si bandit renvoie >0
                    . venv/bin/activate
                    bandit -r app.py test_app.py -f json -o bandit-report.json
                    BANDIT_EXIT=$?
                    echo "Bandit exit code: $BANDIT_EXIT" > bandit-exit-code.txt
                    set -e
                '''
            }
            // archiveArtifacts can help later to download reports from Jenkins UI
            post {
                always {
                    archiveArtifacts artifacts: 'bandit-report.json, bandit-exit-code.txt', allowEmptyArchive: true
                }
            }
        }

        stage('SCA Scan (Snyk)') {
            steps {
                echo 'Lancement Snyk (génère Snyk-report.json)...'
                sh '''
                    set +e
                    . venv/bin/activate

                    # Analyse SCA : sortie JSON dans un fichier
                    snyk test --severity-threshold=high --json > snyk-report.json 2>/dev/null
                    SNYK_EXIT=$?

                    echo "SNYK_EXIT=$SNYK_EXIT" > snyk-exit-code.txt

                    set -e
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'snyk-report.json, snyk-exit-code.txt', allowEmptyArchive: true
                }
            }
        }

        stage('Security Validation') {
            steps {
                echo 'Validation centralisée des rapports Bandit & Snyk...'
                sh '''
                    set -e
                    # --- Bandit validation ---
                    if [ -f bandit-report.json ]; then
                        # compter issues HIGH/CRITICAL dans bandit-report.json (structure Bandit standard)
                        HIGH_COUNT=$(jq '[.results[] | select(.issue_severity=="HIGH" or .issue_severity=="CRITICAL")] | length' bandit-report.json || echo 0)
                    else
                        echo "Attention: bandit-report.json introuvable"
                        HIGH_COUNT=0
                    fi

                    # --- Snyk validation ---
                    # Snyk JSON format: on cherche si la liste 'vulnerabilities' existe et compter
                    if [ -f snyk-report.json ]; then
                        # essayer plusieurs chemins possibles selon version : .vulnerabilities ou .vulnerabilities[]
                        # on utilise try/capture pour éviter erreur jq si la clé n'existe pas
                        SAF_VULNS=$(jq 'if .vulnerabilities then .vulnerabilities | length else 0 end' snyk-report.json || echo 0)
                    else
                        echo "Attention: snyk-report.json introuvable"
                        SAF_VULNS=0
                    fi

                    echo "Bandit HIGH/CRITICAL issues: $HIGH_COUNT"
                    echo "Snyk detected vulnerabilities: $SAF_VULNS"

                    # Politique : échouer si Bandit signale HIGH/CRITICAL ou si Snyk trouve >=1 vulnérabilité
                    if [ "$HIGH_COUNT" -gt 0 ] || [ "$SAF_VULNS" -gt 0 ]; then
                        echo "Vulnérabilités critiques/hautes détectées — échec du pipeline."
                        # On peut afficher un extrait des rapports pour faciliter debug
                        if [ "$HIGH_COUNT" -gt 0 ]; then
                            echo "Extraits Bandit (High/Critical):"
                            jq '.results[] | select(.issue_severity=="HIGH" or .issue_severity=="CRITICAL") | {filename: .filename, test_name: .test_name, issue_text: .issue_text}' bandit-report.json || true
                        fi
                        if [ "$SAF_VULNS" -gt 0 ]; then
                            echo "Extraits Snyk (quelques vulnérabilités):"
                            jq '.vulnerabilities[] | {package_name: .package_name, affected_versions: .affected_versions, advisory: .advisory}' snyk-report.json | head -n 200 || true
                        fi

                        exit 1
                    else
                        echo "Aucun problème critique détecté par Bandit/Snyk."
                    fi
                '''
            }
        }
    } // stages

    post {
        always {
            echo 'Nettoyage...'
            sh 'rm -rf venv'
        }
        success {
            echo 'Pipeline réussi (tests + sécurité OK) !'
        }
        failure {
            echo 'Pipeline échoué (problèmes détectés).'
        }
    }
}