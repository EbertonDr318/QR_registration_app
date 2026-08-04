CREATE DATABASE IF NOT EXISTS registro_qr
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE registro_qr;

CREATE TABLE iglesias (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(160) NOT NULL,
  slug VARCHAR(100) NOT NULL,
  descripcion VARCHAR(500),
  ciudad VARCHAR(120),
  pais VARCHAR(80) NOT NULL DEFAULT 'Guatemala',
  zona_horaria VARCHAR(80) NOT NULL DEFAULT 'America/Guatemala',
  logo_url VARCHAR(500),
  activa BOOLEAN NOT NULL DEFAULT TRUE,
  fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE INDEX ix_iglesias_slug (slug),
  INDEX ix_iglesias_activa (activa)
);

CREATE TABLE personas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  iglesia_id INT NOT NULL,
  codigo VARCHAR(30) NOT NULL,
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
  CONSTRAINT uq_persona_iglesia_codigo UNIQUE (iglesia_id, codigo),
  CONSTRAINT uq_persona_id_iglesia UNIQUE (id, iglesia_id),
  CONSTRAINT fk_persona_iglesia FOREIGN KEY (iglesia_id) REFERENCES iglesias (id),
  INDEX ix_personas_iglesia_id (iglesia_id),
  INDEX idx_persona_correo (correo),
  INDEX idx_persona_estado (activo),
  INDEX idx_persona_sede (sede),
  INDEX idx_persona_grupo (grupo)
);

CREATE TABLE eventos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  iglesia_id INT NOT NULL,
  nombre VARCHAR(120) NOT NULL,
  descripcion VARCHAR(500),
  fecha DATE NOT NULL,
  hora_inicio TIME NOT NULL,
  sede VARCHAR(80),
  estado ENUM('abierto', 'cerrado') NOT NULL DEFAULT 'abierto',
  fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT uq_evento_id_iglesia UNIQUE (id, iglesia_id),
  CONSTRAINT fk_evento_iglesia FOREIGN KEY (iglesia_id) REFERENCES iglesias (id),
  INDEX ix_eventos_iglesia_id (iglesia_id),
  INDEX idx_evento_fecha (fecha),
  INDEX idx_evento_estado (estado)
);

CREATE TABLE asistencias (
  id INT AUTO_INCREMENT PRIMARY KEY,
  iglesia_id INT NOT NULL,
  persona_id INT NOT NULL,
  evento_id INT NOT NULL,
  fecha_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  metodo_registro VARCHAR(20) NOT NULL DEFAULT 'qr',
  CONSTRAINT uq_asistencia_persona_evento UNIQUE (persona_id, evento_id),
  CONSTRAINT fk_asistencia_iglesia FOREIGN KEY (iglesia_id) REFERENCES iglesias (id),
  CONSTRAINT fk_asistencia_persona_iglesia FOREIGN KEY (persona_id, iglesia_id)
    REFERENCES personas (id, iglesia_id) ON DELETE CASCADE,
  CONSTRAINT fk_asistencia_evento_iglesia FOREIGN KEY (evento_id, iglesia_id)
    REFERENCES eventos (id, iglesia_id) ON DELETE CASCADE,
  INDEX ix_asistencias_iglesia_id (iglesia_id),
  INDEX idx_asistencia_fecha (fecha_hora)
);

CREATE TABLE usuarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(120) NOT NULL,
  nombre VARCHAR(160) NOT NULL,
  foto_url VARCHAR(500),
  proveedor VARCHAR(30) NOT NULL DEFAULT 'google',
  proveedor_subject VARCHAR(255),
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  ultimo_acceso DATETIME,
  fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE INDEX ix_usuarios_email (email),
  UNIQUE INDEX ix_usuarios_proveedor_subject (proveedor_subject),
  INDEX ix_usuarios_activo (activo)
);

CREATE TABLE membresias_iglesia (
  id INT AUTO_INCREMENT PRIMARY KEY,
  usuario_id INT NOT NULL,
  iglesia_id INT NOT NULL,
  persona_id INT,
  rol ENUM('usuario', 'admin') NOT NULL DEFAULT 'usuario',
  estado ENUM('pendiente', 'activo', 'suspendido', 'rechazado') NOT NULL DEFAULT 'pendiente',
  fecha_solicitud DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_aprobacion DATETIME,
  aprobado_por_id INT,
  fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT uq_membresia_usuario_iglesia UNIQUE (usuario_id, iglesia_id),
  CONSTRAINT uq_membresia_iglesia_persona UNIQUE (iglesia_id, persona_id),
  CONSTRAINT fk_membresia_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE,
  CONSTRAINT fk_membresia_iglesia FOREIGN KEY (iglesia_id) REFERENCES iglesias (id) ON DELETE CASCADE,
  CONSTRAINT fk_membresia_persona_iglesia FOREIGN KEY (persona_id, iglesia_id)
    REFERENCES personas (id, iglesia_id),
  CONSTRAINT fk_membresia_aprobador FOREIGN KEY (aprobado_por_id) REFERENCES usuarios (id) ON DELETE SET NULL,
  INDEX ix_membresias_usuario_id (usuario_id),
  INDEX ix_membresias_iglesia_id (iglesia_id),
  INDEX ix_membresias_estado (estado),
  INDEX ix_membresias_rol (rol)
);

CREATE TABLE registros_auditoria (
  id INT AUTO_INCREMENT PRIMARY KEY,
  iglesia_id INT NOT NULL,
  actor_usuario_id INT,
  accion VARCHAR(80) NOT NULL,
  entidad VARCHAR(80) NOT NULL,
  entidad_id INT,
  detalles TEXT,
  fecha_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_auditoria_iglesia FOREIGN KEY (iglesia_id) REFERENCES iglesias (id),
  CONSTRAINT fk_auditoria_actor FOREIGN KEY (actor_usuario_id) REFERENCES usuarios (id) ON DELETE SET NULL,
  INDEX ix_auditoria_iglesia_id (iglesia_id),
  INDEX ix_auditoria_fecha_hora (fecha_hora),
  INDEX ix_auditoria_accion (accion)
);
