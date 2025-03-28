# aws cloudformation delete-stack --stack-name HanzoflowAppStack
aws ecr delete-repository --repository-name hanzoflow-backend-repository --force
# aws ecr delete-repository --repository-name hanzoflow-frontend-repository --force
# aws ecr describe-repositories --output json | jq -re ".repositories[].repositoryName"