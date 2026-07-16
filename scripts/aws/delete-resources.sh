# aws cloudformation delete-stack --stack-name HanzoFlowAppStack
aws ecr delete-repository --repository-name flow-backend-repository --force
# aws ecr delete-repository --repository-name flow-frontend-repository --force
# aws ecr describe-repositories --output json | jq -re ".repositories[].repositoryName"