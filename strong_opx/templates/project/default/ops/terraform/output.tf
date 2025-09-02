resource "null_resource" "update-config" {
  triggers = {
  }

  provisioner "local-exec" {
    command = <<HEREDOC
cat<<EOF > ${path.module}/../environments/${var.ENVIRONMENT}/config.yml
aws:
  region: '${var.AWS_REGION}'
EOF
HEREDOC
  }
}
