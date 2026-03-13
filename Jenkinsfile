pipeline {
    agent any
    
    triggers {
        githubPush()
    }

    environment {
        SONAR_PROJECT = 'nexus-agentic-ai'
        DOCKER_REGISTRY = 'docker.io'
        DOCKER_CREDENTIALS_ID = 'docker-cred'
        DOCKER_USERNAME = 'trahulprabhu38'
        K8S_NAMESPACE = 'default'
        GIT_COMMIT_SHORT = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
        BUILD_TAG = "${env.BUILD_NUMBER}-${GIT_COMMIT_SHORT}"
    }

    parameters {
        booleanParam(name: 'BUILD_SQL_QUERY_GEN', defaultValue: true, description: 'Build SQL Query Generator')
        booleanParam(name: 'BUILD_INTENT_AGENT', defaultValue: true, description: 'Build Intent Agent')
        booleanParam(name: 'BUILD_SQL_VALIDATOR', defaultValue: true, description: 'Build SQL Validator Agent')
        booleanParam(name: 'BUILD_COLUMN_PRUNING', defaultValue: true, description: 'Build Column Pruning')
        booleanParam(name: 'BUILD_FRONTEND', defaultValue: true, description: 'Build Frontend')
        booleanParam(name: 'PUSH_TO_REGISTRY', defaultValue: true, description: 'Push images to Docker registry')
        booleanParam(name: 'DEPLOY_TO_K8S', defaultValue: false, description: 'Deploy to Kubernetes cluster')
        choice(name: 'TAG_VERSION', choices: ['latest', 'v1', 'v2', 'custom'], description: 'Docker image tag version')
        string(name: 'CUSTOM_TAG', defaultValue: '', description: 'Custom tag (if TAG_VERSION is custom)')
    }

    stages {
        stage("Git Checkout") {
            steps {
                git branch: 'main',
                    credentialsId: 'git-cred',
                    url: 'https://github.com/trahulprabhu38/nexus-AgenticAI'
            }
        }
        stage("SonarQube Analysis") {
            steps {
                withSonarQubeEnv('sonarqube') {
                    sh '''
                    sonar-scanner \
                      -Dsonar.projectKey=nexus-agentic-ai \
                      -Dsonar.projectName="nexus-agentic-ai" \
                      -Dsonar.sources=. \
                      -Dsonar.language=py \
                      -Dsonar.python.version=3
                    '''
                }
            }
        }
        stage("Quality Gate") {
            steps {
                timeout(time: 3, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }
        stage('Environment Setup') {
            steps {
                script {
                    env.IMAGE_TAG = params.TAG_VERSION == 'custom' && params.CUSTOM_TAG ? params.CUSTOM_TAG : params.TAG_VERSION
                    echo "Docker Image Tag: ${env.IMAGE_TAG}"
                    echo "Build Tag: ${env.BUILD_TAG}"
                }
            }
        }

        stage('Build Docker Images') {
            parallel {
                stage('SQL Query Generator') {
                    when {
                        expression { params.BUILD_SQL_QUERY_GEN == true }
                    }
                    steps {
                        script {
                            echo "Building SQL Query Generator..."
                            dir('SQL_QUERY_GENERATOR') {
                                sh """
                                    docker build \
                                        -t ${DOCKER_USERNAME}/sql-query-gen:${IMAGE_TAG} \
                                        -t ${DOCKER_USERNAME}/sql-query-gen:${BUILD_TAG} \
                                        --build-arg BUILD_DATE=\$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
                                        --build-arg VCS_REF=${GIT_COMMIT_SHORT} \
                                        .
                                """
                            }
                            echo "SQL Query Generator build completed"
                        }
                    }
                }

                stage('Intent Agent') {
                    when {
                        expression { params.BUILD_INTENT_AGENT == true }
                    }
                    steps {
                        script {
                            echo "Building Intent Agent (this may take longer due to model download)..."
                            dir('Intent-Agent') {
                                sh """
                                    docker build \
                                        -t ${DOCKER_USERNAME}/intent-agent:${IMAGE_TAG} \
                                        -t ${DOCKER_USERNAME}/intent-agent:${BUILD_TAG} \
                                        --build-arg BUILD_DATE=\$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
                                        --build-arg VCS_REF=${GIT_COMMIT_SHORT} \
                                        .
                                """
                            }
                            echo "Intent Agent build completed"
                        }
                    }
                }

                stage('SQL Validator Agent') {
                    when {
                        expression { params.BUILD_SQL_VALIDATOR == true }
                    }
                    steps {
                        script {
                            echo "Building SQL Validator Agent..."
                            dir('sql_validator_agent') {
                                sh """
                                    docker build \
                                        -t ${DOCKER_USERNAME}/sql-validator:${IMAGE_TAG} \
                                        -t ${DOCKER_USERNAME}/sql-validator:${BUILD_TAG} \
                                        --build-arg BUILD_DATE=\$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
                                        --build-arg VCS_REF=${GIT_COMMIT_SHORT} \
                                        .
                                """
                            }
                            echo "SQL Validator Agent build completed"
                        }
                    }
                }

                stage('Column Pruning') {
                    when {
                        expression { params.BUILD_COLUMN_PRUNING == true }
                    }
                    steps {
                        script {
                            echo "Building Column Pruning Service..."
                            dir('column pruning') {
                                sh """
                                    docker build \
                                        -t ${DOCKER_USERNAME}/column-prune:${IMAGE_TAG} \
                                        -t ${DOCKER_USERNAME}/column-prune:${BUILD_TAG} \
                                        --build-arg BUILD_DATE=\$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
                                        --build-arg VCS_REF=${GIT_COMMIT_SHORT} \
                                        .
                                """
                            }
                            echo "Column Pruning build completed"
                        }
                    }
                }

                stage('Frontend') {
                    when {
                        expression { params.BUILD_FRONTEND == true }
                    }
                    steps {
                        script {
                            echo "Building Frontend (Multi-stage build)..."
                            dir('frontend') {
                                sh """
                                    docker build \
                                        -t ${DOCKER_USERNAME}/nexus-frontend:${IMAGE_TAG} \
                                        -t ${DOCKER_USERNAME}/nexus-frontend:${BUILD_TAG} \
                                        --build-arg BUILD_DATE=\$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
                                        --build-arg VCS_REF=${GIT_COMMIT_SHORT} \
                                        .
                                """
                            }
                            echo "Frontend build completed"
                        }
                    }
                }
            }
        }

        // stage('Run Tests') {
        //     parallel {
        //         stage('Test SQL Validator') {
        //             when {
        //                 expression { params.BUILD_SQL_VALIDATOR == true }
        //             }
        //             steps {
        //                 script {
        //                     echo "Running SQL Validator tests..."
        //                     dir('sql_validator_agent') {
        //                         sh """
        //                             docker run --rm \
        //                                 ${DOCKER_USERNAME}/sql-validator:${BUILD_TAG} \
        //                                 python -m pytest test_validator.py -v || true
        //                         """
        //                     }
        //                 }
        //             }
        //         }

        //         stage('Security Scan') {
        //             steps {
        //                 script {
        //                     echo "Running security scans on images..."
        //                     // Using Trivy for container security scanning
        //                     sh """
        //                         # Install trivy if not already installed
        //                         which trivy || (
        //                             wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
        //                             echo "deb https://aquasecurity.github.io/trivy-repo/deb \$(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
        //                             sudo apt-get update
        //                             sudo apt-get install trivy
        //                         ) || echo "Trivy installation skipped"
        //                     """
        //                 }
        //             }
        //         }
        //     }
        // }

        stage('Push to Registry') {
            when {
                expression { params.PUSH_TO_REGISTRY == true }
            }
            steps {
                script {
                    echo "Logging into Docker registry..."
                    withCredentials([usernamePassword(credentialsId: "${DOCKER_CREDENTIALS_ID}",
                                                     usernameVariable: 'DOCKER_USER',
                                                     passwordVariable: 'DOCKER_PASS')]) {
                        sh 'echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin'
                    }

                    parallel(
                        'Push SQL Query Gen': {
                            if (params.BUILD_SQL_QUERY_GEN) {
                                echo "Pushing SQL Query Generator..."
                                sh """
                                    docker push ${DOCKER_USERNAME}/sql-query-gen:${IMAGE_TAG}
                                    docker push ${DOCKER_USERNAME}/sql-query-gen:${BUILD_TAG}
                                """
                            }
                        },
                        'Push Intent Agent': {
                            if (params.BUILD_INTENT_AGENT) {
                                echo "Pushing Intent Agent..."
                                sh """
                                    docker push ${DOCKER_USERNAME}/intent-agent:${IMAGE_TAG}
                                    docker push ${DOCKER_USERNAME}/intent-agent:${BUILD_TAG}
                                """
                            }
                        },
                        'Push SQL Validator': {
                            if (params.BUILD_SQL_VALIDATOR) {
                                echo "Pushing SQL Validator..."
                                sh """
                                    docker push ${DOCKER_USERNAME}/sql-validator:${IMAGE_TAG}
                                    docker push ${DOCKER_USERNAME}/sql-validator:${BUILD_TAG}
                                """
                            }
                        },
                        'Push Column Pruning': {
                            if (params.BUILD_COLUMN_PRUNING) {
                                echo "Pushing Column Pruning..."
                                sh """
                                    docker push ${DOCKER_USERNAME}/column-prune:${IMAGE_TAG}
                                    docker push ${DOCKER_USERNAME}/column-prune:${BUILD_TAG}
                                """
                            }
                        },
                        'Push Frontend': {
                            if (params.BUILD_FRONTEND) {
                                echo "Pushing Frontend..."
                                sh """
                                    docker push ${DOCKER_USERNAME}/nexus-frontend:${IMAGE_TAG}
                                    docker push ${DOCKER_USERNAME}/nexus-frontend:${BUILD_TAG}
                                """
                            }
                        }
                    )

                    echo "All images pushed successfully"
                }
            }
        }

        stage('Deploy to Kubernetes') {
            when {
                expression { params.DEPLOY_TO_K8S == true }
            }
            steps {
                script {
                    echo "Deploying to Kubernetes..."

                    // Update image tags in deployments
                    sh """
                        # Update SQL Query Generator
                        if [ "${params.BUILD_SQL_QUERY_GEN}" = "true" ]; then
                            kubectl set image deployment/sql-query-gen-deployment \
                                sql-query-gen=${DOCKER_USERNAME}/sql-query-gen:${IMAGE_TAG} \
                                -n ${K8S_NAMESPACE}
                        fi

                        # Update Intent Agent
                        if [ "${params.BUILD_INTENT_AGENT}" = "true" ]; then
                            kubectl set image deployment/intent-agent-deployment \
                                intent-agent=${DOCKER_USERNAME}/intent-agent:${IMAGE_TAG} \
                                -n ${K8S_NAMESPACE}
                        fi

                        # Update SQL Validator
                        if [ "${params.BUILD_SQL_VALIDATOR}" = "true" ]; then
                            kubectl set image deployment/sql-validator-api-deployment \
                                sql-validator=${DOCKER_USERNAME}/sql-validator:${IMAGE_TAG} \
                                -n ${K8S_NAMESPACE}
                        fi

                        # Update Column Pruning
                        if [ "${params.BUILD_COLUMN_PRUNING}" = "true" ]; then
                            kubectl set image deployment/column-prune-deployment \
                                column-prune=${DOCKER_USERNAME}/column-prune:${IMAGE_TAG} \
                                -n ${K8S_NAMESPACE}
                        fi

                        # Update Frontend
                        if [ "${params.BUILD_FRONTEND}" = "true" ]; then
                            kubectl set image deployment/frontend-deployment \
                                frontend=${DOCKER_USERNAME}/nexus-frontend:${IMAGE_TAG} \
                                -n ${K8S_NAMESPACE}
                        fi
                    """

                    // Wait for rollout
                    echo "Waiting for deployments to complete..."
                    sh """
                        kubectl rollout status deployment/sql-query-gen-deployment -n ${K8S_NAMESPACE} --timeout=5m || true
                        kubectl rollout status deployment/intent-agent-deployment -n ${K8S_NAMESPACE} --timeout=5m || true
                        kubectl rollout status deployment/sql-validator-api-deployment -n ${K8S_NAMESPACE} --timeout=5m || true
                        kubectl rollout status deployment/column-prune-deployment -n ${K8S_NAMESPACE} --timeout=5m || true
                        kubectl rollout status deployment/frontend-deployment -n ${K8S_NAMESPACE} --timeout=5m || true
                    """
                }
            }
        }

        stage('Verify Deployment') {
            when {
                expression { params.DEPLOY_TO_K8S == true }
            }
            steps {
                script {
                    echo "Verifying deployment health..."
                    sh """
                        echo "=== Deployment Status ==="
                        kubectl get deployments -n ${K8S_NAMESPACE}

                        echo "=== Pod Status ==="
                        kubectl get pods -n ${K8S_NAMESPACE}

                        echo "=== Service Status ==="
                        kubectl get services -n ${K8S_NAMESPACE}
                    """
                }
            }
        }
    }

    post {
        always {
            script {
                echo "Pipeline execution completed"
                sh 'docker logout || true'
            }
        }
        success {
            echo "Build and deployment successful!"
            script {
                // Clean up old images to save space
                sh """
                    docker image prune -f
                    echo "Cleaned up dangling images"
                """
            }
        }
        failure {
            echo "Build or deployment failed. Check logs for details."
        }
        cleanup {
            cleanWs()
        }
    }
}
