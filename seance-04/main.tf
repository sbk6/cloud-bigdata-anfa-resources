# main.tf — version paramétrée
# ─────────────────────────────

terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

resource "docker_network" "anfa_net" {
  name = "anfa-network"
}

resource "docker_volume" "minio_data" {
  name = "anfa-minio-data-tf"
}

resource "docker_image" "minio" {
  name = "minio/minio:latest"
}

resource "docker_container" "minio" {
  name    = var.container_name
  image   = docker_image.minio.image_id
  command = ["server", "/data", "--console-address", ":9001"]
  restart = "unless-stopped"

  ports {
    internal = 9000
    external = var.minio_api_port
  }

  ports {
    internal = 9001
    external = var.minio_console_port
  }

  env = [
    "MINIO_ROOT_USER=${var.minio_root_user}",
    "MINIO_ROOT_PASSWORD=${var.minio_root_password}",
  ]

  volumes {
    volume_name    = docker_volume.minio_data.name
    container_path = "/data"
  }

  networks_advanced {
    name = docker_network.anfa_net.name
  }

  lifecycle {
    ignore_changes = [log_opts]
  }
}
