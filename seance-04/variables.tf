variable "minio_root_user" {
  description = "Nom d'utilisateur administrateur MinIO"
  type        = string
  default     = "anfa-admin"
}

variable "minio_root_password" {
  description = "Mot de passe administrateur MinIO"
  type        = string
  sensitive   = true
}

variable "minio_api_port" {
  description = "Port hôte pour l'API MinIO"
  type        = number
  default     = 9010
}

variable "minio_console_port" {
  description = "Port hôte pour la console MinIO"
  type        = number
  default     = 9011
}

variable "container_name" {
  description = "Nom du conteneur MinIO"
  type        = string
  default     = "anfa-minio-tf"
}
