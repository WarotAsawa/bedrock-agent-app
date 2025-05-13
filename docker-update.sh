echo "Building Docker image and tagging"
docker build -t bedrock-agent-app:test .
docker tag bedrock-agent-app:test 638806779113.dkr.ecr.us-east-1.amazonaws.com/bedrock-agent-app:test

echo "Loggin into ECR"
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 638806779113.dkr.ecr.us-east-1.amazonaws.com

echo "Pusing Image into ECR"
docker push 638806779113.dkr.ecr.us-east-1.amazonaws.com/bedrock-agent-app:test

echo "Updating ECR Services"
aws ecs update-service --cluster gen-ai-km-demo --service agent-warot-svc --force-new-deployment --region us-east-1
echo "Finishing updating ECR Services"
