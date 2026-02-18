PRAGMA foreign_keys = ON;

-- Users who can authenticate into the app.
CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  email TEXT UNIQUE,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- Experiment is the top-level container and owner boundary.
CREATE TABLE IF NOT EXISTS experiments (
  experiment_id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  experiment_date TEXT NOT NULL,
  conditions_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','active','completed','archived')),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  FOREIGN KEY (owner_user_id) REFERENCES users(user_id) ON DELETE RESTRICT
);

-- Access control for experiment collaborators.
-- role semantics:
-- owner: full control (typically implicit from experiments.owner_user_id)
-- collaborator: can edit slides + add notes
-- viewer: read-only data, can_add_notes=1 allows notes without data modification
CREATE TABLE IF NOT EXISTS experiment_members (
  experiment_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('owner','collaborator','viewer')),
  can_add_notes INTEGER NOT NULL DEFAULT 1 CHECK (can_add_notes IN (0,1)),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  PRIMARY KEY (experiment_id, user_id),
  FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS treatment_groups (
  group_id TEXT PRIMARY KEY,
  experiment_id TEXT NOT NULL,
  name TEXT NOT NULL,
  sort_order INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE (experiment_id, name),
  FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id) ON DELETE CASCADE
);

-- Protocol defaults at experiment level. Slides can override any field.
CREATE TABLE IF NOT EXISTS experiment_protocol_defaults (
  experiment_id TEXT PRIMARY KEY,
  detergent_type TEXT,
  detergent_concentration_value REAL,
  detergent_concentration_unit TEXT,
  serum_type TEXT,
  serum_concentration_value REAL,
  serum_concentration_unit TEXT,
  blocking_agent TEXT,
  block_concentration_value REAL,
  block_concentration_unit TEXT,
  block_duration_minutes INTEGER,
  primary_incubation_minutes INTEGER,
  secondary_block_minutes INTEGER,
  secondary_incubation_minutes INTEGER,
  edu_used INTEGER NOT NULL DEFAULT 0 CHECK (edu_used IN (0,1)),
  dapi_concentration_value REAL,
  dapi_concentration_unit TEXT,
  dapi_incubation_minutes INTEGER,
  mounting_medium TEXT,
  notes TEXT,
  FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS slides (
  slide_id TEXT PRIMARY KEY,
  experiment_id TEXT NOT NULL,
  group_id TEXT NOT NULL,
  owner_user_id TEXT NOT NULL,
  local_label TEXT,
  specimen_origin_json TEXT NOT NULL DEFAULT '{}',
  experiment_overrides_json TEXT NOT NULL DEFAULT '{}',
  storage_location TEXT,
  pre_imaged_photo_path TEXT,
  imaged INTEGER NOT NULL DEFAULT 0 CHECK (imaged IN (0,1)),
  imaging_site TEXT,
  imaging_notes TEXT,
  cell_count_data_link TEXT,
  status TEXT NOT NULL DEFAULT 'in_storage' CHECK (status IN ('in_storage','checked_out','imaged','archived','destroyed')),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id) ON DELETE CASCADE,
  FOREIGN KEY (group_id) REFERENCES treatment_groups(group_id) ON DELETE CASCADE,
  FOREIGN KEY (owner_user_id) REFERENCES users(user_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_slides_experiment ON slides(experiment_id);
CREATE INDEX IF NOT EXISTS idx_slides_group ON slides(group_id);
CREATE INDEX IF NOT EXISTS idx_slides_owner ON slides(owner_user_id);

CREATE TABLE IF NOT EXISTS antibodies (
  antibody_id TEXT PRIMARY KEY,
  target_name TEXT NOT NULL,
  host_species TEXT,
  clone_name TEXT,
  vendor TEXT,
  catalog_number TEXT,
  lot_number TEXT,
  is_secondary INTEGER NOT NULL DEFAULT 0 CHECK (is_secondary IN (0,1)),
  recommended_for_host_species TEXT,
  fluorophore TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS slide_primary_antibodies (
  slide_id TEXT NOT NULL,
  antibody_id TEXT NOT NULL,
  dilution_value REAL,
  dilution_unit TEXT,
  incubation_minutes INTEGER,
  notes TEXT,
  PRIMARY KEY (slide_id, antibody_id),
  FOREIGN KEY (slide_id) REFERENCES slides(slide_id) ON DELETE CASCADE,
  FOREIGN KEY (antibody_id) REFERENCES antibodies(antibody_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS slide_secondary_antibodies (
  slide_id TEXT NOT NULL,
  antibody_id TEXT NOT NULL,
  dilution_value REAL,
  dilution_unit TEXT,
  incubation_minutes INTEGER,
  notes TEXT,
  PRIMARY KEY (slide_id, antibody_id),
  FOREIGN KEY (slide_id) REFERENCES slides(slide_id) ON DELETE CASCADE,
  FOREIGN KEY (antibody_id) REFERENCES antibodies(antibody_id) ON DELETE RESTRICT
);

-- Per-slide EdU details only when used.
CREATE TABLE IF NOT EXISTS slide_edu_conditions (
  edu_condition_id TEXT PRIMARY KEY,
  slide_id TEXT NOT NULL,
  concentration_value REAL NOT NULL,
  concentration_unit TEXT NOT NULL,
  incubation_minutes INTEGER NOT NULL,
  notes TEXT,
  FOREIGN KEY (slide_id) REFERENCES slides(slide_id) ON DELETE CASCADE
);

-- Images and external assets linked to the slide.
CREATE TABLE IF NOT EXISTS slide_assets (
  asset_id TEXT PRIMARY KEY,
  slide_id TEXT NOT NULL,
  asset_type TEXT NOT NULL CHECK (asset_type IN (
    'pre_image_photo',
    'microscopy_image',
    'czi_raw',
    'cell_count_data',
    'presentation_reference',
    'other'
  )),
  uri TEXT NOT NULL,
  content_hash TEXT,
  captured_at TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_by_user_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  FOREIGN KEY (slide_id) REFERENCES slides(slide_id) ON DELETE CASCADE,
  FOREIGN KEY (created_by_user_id) REFERENCES users(user_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_slide_assets_slide ON slide_assets(slide_id);
CREATE INDEX IF NOT EXISTS idx_slide_assets_type ON slide_assets(asset_type);

-- Notes are append-only records and can be added by non-owners if can_add_notes=1.
CREATE TABLE IF NOT EXISTS slide_notes (
  note_id TEXT PRIMARY KEY,
  slide_id TEXT NOT NULL,
  author_user_id TEXT NOT NULL,
  note_type TEXT NOT NULL CHECK (note_type IN ('general','imaging','storage','analysis','presentation')),
  body TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  FOREIGN KEY (slide_id) REFERENCES slides(slide_id) ON DELETE CASCADE,
  FOREIGN KEY (author_user_id) REFERENCES users(user_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_slide_notes_slide ON slide_notes(slide_id);
CREATE INDEX IF NOT EXISTS idx_slide_notes_author ON slide_notes(author_user_id);

-- Captures where slides were used (ppt, manuscript, report, counting pipeline).
CREATE TABLE IF NOT EXISTS slide_usage_events (
  usage_event_id TEXT PRIMARY KEY,
  slide_id TEXT NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('presentation','cell_counting','figure_export','publication','other')),
  location_or_uri TEXT,
  description TEXT,
  event_date TEXT,
  created_by_user_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  FOREIGN KEY (slide_id) REFERENCES slides(slide_id) ON DELETE CASCADE,
  FOREIGN KEY (created_by_user_id) REFERENCES users(user_id) ON DELETE RESTRICT
);

-- Immutable audit log of data edits. app layer should write one entry per change.
CREATE TABLE IF NOT EXISTS audit_log (
  audit_id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  action TEXT NOT NULL CHECK (action IN ('create','update','delete')),
  changed_by_user_id TEXT NOT NULL,
  changed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  before_json TEXT,
  after_json TEXT,
  FOREIGN KEY (changed_by_user_id) REFERENCES users(user_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(changed_by_user_id);

-- Helpful compatibility view: all slide notes + direct imaging_notes field.
CREATE VIEW IF NOT EXISTS v_slide_all_notes AS
SELECT
  s.slide_id,
  'imaging' AS note_type,
  s.imaging_notes AS body,
  s.updated_at AS created_at,
  s.owner_user_id AS author_user_id
FROM slides s
WHERE s.imaging_notes IS NOT NULL AND trim(s.imaging_notes) <> ''
UNION ALL
SELECT
  n.slide_id,
  n.note_type,
  n.body,
  n.created_at,
  n.author_user_id
FROM slide_notes n;
