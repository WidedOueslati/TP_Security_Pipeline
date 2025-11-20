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

        stage('Setup Python Environment & Tools') {
            steps {
                echo 'Configuration de l\'environnement Python et installation outils (bandit, safety, jq)...'
                sh '''
                    set -e
                    python3 -m venv venv
                    . venv/bin/activate
                    
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    # Installer Nikto (scan de sécurité)
                    if [ ! -d "nikto" ]; then
                        echo "Installation de Nikto..."
                        git clone https://github.com/sullo/nikto.git
                    else
                        echo "Nikto déjà installé, mise à jour..."
                        cd nikto && git pull && cd ..
                    fi
                    pip install bandit safety    # installe Bandit et Safety
                    # vérifie jq (si absent, tenter d'installer via apt-get si possible)
                    if ! command -v jq >/dev/null 2>&1; then
                        echo "jq non trouvé - tentative d'installation (si l'agent le permet)..."
                        if [ -f /etc/debian_version ]; then
                            sudo apt-get update && sudo apt-get install -y jq || true
                        fi
                    fi
                    echo "Outils installés : $(bandit --version 2>/dev/null || echo 'bandit?') / $(safety check --version 2>/dev/null || echo 'safety?') / jq: $(jq --version 2>/dev/null || echo 'jq?')"
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

        stage('SCA Scan (Safety)') {
            steps {
                echo 'Lancement Safety (génère safety-report.json)...'
                sh '''
                    set +e
                    . venv/bin/activate
                    # safety peut lire requirements.txt ; on force la sortie JSON dans un fichier
                    safety check --full-report --file=requirements.txt --json > safety-report.json 2>/dev/null
                    SAFETY_EXIT=$?
                    echo "SAFETY_EXIT=$SAFETY_EXIT" > safety-exit-code.txt
                    set -e
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'safety-report.json, safety-exit-code.txt', allowEmptyArchive: true
                }
            }
        }
        
        stage('Security Validation') {
            steps {
                echo 'Validation centralisée des rapports Bandit & Safety...'
                sh '''
                    set -e
                    # --- Bandit validation ---
                    if [ -f bandit-report.json ]; then
                        HIGH_COUNT=$(jq '[.results[] | select(.issue_severity=="HIGH" or .issue_severity=="CRITICAL")] | length' bandit-report.json || echo 0)
                    else
                        echo "Attention: bandit-report.json introuvable"
                        HIGH_COUNT=0
                    fi

                    # --- Safety validation ---
                    if [ -f safety-report.json ]; then
                        SAF_VULNS=$(jq 'if .vulnerabilities then .vulnerabilities | length else 0 end' safety-report.json || echo 0)
                    else
                        echo "Attention: safety-report.json introuvable"
                        SAF_VULNS=0
                    fi

                    echo "Bandit HIGH/CRITICAL issues: $HIGH_COUNT"
                    echo "Safety detected vulnerabilities: $SAF_VULNS"

                    # Politique : échouer si Bandit signale HIGH/CRITICAL ou si Safety trouve >=1 vulnérabilité
                    if [ "$HIGH_COUNT" -gt 0 ] || [ "$SAF_VULNS" -gt 0 ]; then
                        echo "Vulnérabilités critiques/hautes détectées — échec du pipeline."
                        if [ "$HIGH_COUNT" -gt 0 ]; then
                            echo "Extraits Bandit (High/Critical):"
                            jq '.results[] | select(.issue_severity=="HIGH" or .issue_severity=="CRITICAL") | {filename: .filename, test_name: .test_name, issue_text: .issue_text}' bandit-report.json || true
                        fi
                        if [ "$SAF_VULNS" -gt 0 ]; then
                            echo "Extraits Safety (quelques vulnérabilités):"
                            jq '.vulnerabilities[] | {package_name: .package_name, affected_versions: .affected_versions, advisory: .advisory}' safety-report.json | head -n 200 || true
                        fi

                        exit 1
                    else
                        echo "Aucun problème critique détecté par Bandit/Safety."
                    fi
                '''
            }
        }

        stage('Deploy Temporary App') {
            steps {
                echo "Déploiement de l'application Flask pour le scan DAST..."
                sh '''
                    # Activate Python venv
                    . venv/bin/activate
                    
                    # Create a small Python runner for Flask
                    cat > run_flask.py << 'EOF'
        from app import app
        if __name__ == '__main__':
            # Bind to 0.0.0.0 so other containers on the network can reach it
            app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
        EOF

                    # Launch Flask in background
                    nohup python run_flask.py > flask.log 2>&1 &
                    echo $! > flask.pid

                    # Wait for Flask to be ready
                    sleep 10

                    # Check logs briefly
                    echo "=== Flask logs ==="
                    tail -n 20 flask.log

                    # Optional: test container-local access
                    curl -I http://127.0.0.1:5000 || echo "Flask not ready on localhost"

                    # Show container IPs (for ZAP to connect)
                    hostname -I
                '''
            }
        }

        stage('DAST Scan - OWASP ZAP') {
            steps {
                echo 'Running OWASP ZAP Baseline Scan...'
                sh '''
                    set +e  # Don't fail immediately on non-zero exit
                    
                    WORKDIR=/zap/wrk
                    
                    # Fix permissions in the workspace
                    docker run --rm -v $(pwd):$WORKDIR alpine sh -c "chown -R 1000:1000 $WORKDIR"
                    
                    # Use container name for ZAP target
                    FLASK_HOST=jenkins2  # Replace with your Jenkins container name on the bridge network
                    
                    # Create the workspace directory inside container if it doesn't exist
                    mkdir -p $(pwd)/zap-reports
                    
                    docker run --rm --network devsecops-net \
                        -v $(pwd):$WORKDIR:rw \
                        ghcr.io/zaproxy/zaproxy:stable \
                        zap-baseline.py \
                        -t http://$FLASK_HOST:5000 \
                        -r $WORKDIR/zap-reports/zap-report.html \
                        -J $WORKDIR/zap-reports/zap-report.json \
                        -x $WORKDIR/zap-reports/zap-report.xml
                    
                    ZAP_EXIT=$?
                    echo "ZAP exit code: $ZAP_EXIT" > zap-reports/zap-exit-code.txt
                    
                    # Check if reports were generated
                    if [ -f "zap-reports/zap-report.html" ]; then
                        echo "HTML report generated successfully"
                        head -n 20 zap-reports/zap-report.html
                    else
                        echo "WARNING: HTML report was not generated"
                    fi
                    
                    if [ -f "zap-reports/zap-report.json" ]; then
                        echo "JSON report generated successfully"
                        # Show just the first few lines of JSON to verify structure
                        head -n 10 zap-reports/zap-report.json
                    else
                        echo "WARNING: JSON report was not generated"
                    fi
                    
                    set -e  # Restore default fail-on-error
                    
                    # Verify reports with better error handling
                    echo "Checking generated files:"
                    ls -lh zap-reports/ || true
                    echo "File sizes:"
                    du -sh zap-reports/* 2>/dev/null || echo "No reports found in zap-reports directory"
                    
                    # ZAP often exits with non-zero for warnings, which might be acceptable
                    if [ $ZAP_EXIT -eq 0 ]; then
                        echo "ZAP scan completed successfully"
                    elif [ $ZAP_EXIT -eq 1 ]; then
                        echo "ZAP scan completed with warnings"
                    elif [ $ZAP_EXIT -eq 2 ]; then
                        echo "ZAP scan failed with errors"
                        exit 1
                    else
                        echo "ZAP scan completed with unknown exit code: $ZAP_EXIT"
                    fi
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'zap-report.html, zap-report.json', allowEmptyArchive: true
                }
            }
        }

        stage('Stop Temporary App') {
            steps {
                sh '''
                    if [ -f flask.pid ]; then
                        kill $(cat flask.pid)
                        rm flask.pid
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
            echo 'Pipeline réussi  !'
        }
        failure {
            echo 'Pipeline échoué (problèmes détectés).'
        }
    }
}
