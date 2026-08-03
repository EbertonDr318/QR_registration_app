CREATE DATABASE IF NOT EXISTS registro_qr
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE registro_qr;

CREATE TABLE personas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  codigo VARCHAR(30) NOT NULL UNIQUE,
  nombres VARCHAR(80) NOT NULL,
  apellidos VARCHAR(80) NOT NULL,
  correo VARCHAR(120),
  telefono VARCHAR(25),
  sede VARCHAR(80),
  grupo VARCHAR(80),
  qr_token VARCHAR(64) NOT NULL UNIQUE,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_persona_estado (activo),
  INDEX idx_persona_sede (sede),
  INDEX idx_persona_grupo (grupo)
);

CREATE TABLE eventos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL,
  descripcion VARCHAR(500),
  fecha DATE NOT NULL,
  hora_inicio TIME NOT NULL,
  sede VARCHAR(80),
  estado ENUM('abierto', 'cerrado') NOT NULL DEFAULT 'abierto',
  fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_evento_fecha (fecha),
  INDEX idx_evento_estado (estado)
);

CREATE TABLE asistencias (
  id INT AUTO_INCREMENT PRIMARY KEY,
  persona_id INT NOT NULL,
  evento_id INT NOT NULL,
  fecha_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  metodo_registro VARCHAR(20) NOT NULL DEFAULT 'qr',
  CONSTRAINT uq_asistencia_persona_evento UNIQUE (persona_id, evento_id),
  CONSTRAINT fk_asistencia_persona FOREIGN KEY (persona_id) REFERENCES personas (id) ON DELETE CASCADE,
  CONSTRAINT fk_asistencia_evento FOREIGN KEY (evento_id) REFERENCES eventos (id) ON DELETE CASCADE,
  INDEX idx_asistencia_fecha (fecha_hora)
);

CREATE TABLE usuarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(120) NOT NULL,
  nombre VARCHAR(160) NOT NULL,
  foto_url VARCHAR(500),
  proveedor VARCHAR(30) NOT NULL DEFAULT 'google',
  proveedor_subject VARCHAR(255),
  rol VARCHAR(20) NOT NULL DEFAULT 'usuario',
  persona_id INT,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  ultimo_acceso DATETIME,
  fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT uq_usuario_proveedor_subject UNIQUE (proveedor, proveedor_subject),
  CONSTRAINT ck_usuario_rol CHECK (rol IN ('usuario', 'admin')),
  CONSTRAINT fk_usuario_persona FOREIGN KEY (persona_id) REFERENCES personas (id) ON DELETE SET NULL,
  UNIQUE INDEX ix_usuarios_email (email),
  INDEX idx_usuario_rol (rol),
  INDEX idx_usuario_activo (activo),
  UNIQUE INDEX ix_usuarios_persona_id (persona_id)
);
