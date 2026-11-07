-- Esquema de referencia generado desde backend/app/models.py (SQLAlchemy).
-- La aplicación crea las tablas automáticamente al iniciar; este archivo es documentación.
-- Dialecto: PostgreSQL. Para SQLite, los tipos equivalentes los resuelve SQLAlchemy.

CREATE TABLE app_meta (
	key VARCHAR(60) NOT NULL, 
	value TEXT NOT NULL, 
	PRIMARY KEY (key)
);

CREATE TABLE areas (
	id SERIAL NOT NULL, 
	name VARCHAR(80) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE merchants (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE products (
	id SERIAL NOT NULL, 
	code VARCHAR(40) NOT NULL, 
	name VARCHAR(80) NOT NULL, 
	color VARCHAR(9) NOT NULL, 
	model_label VARCHAR(40), 
	active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);

CREATE TABLE lots (
	id SERIAL NOT NULL, 
	code VARCHAR(24) NOT NULL, 
	product_id INTEGER NOT NULL, 
	merchant_id INTEGER NOT NULL, 
	area_id INTEGER NOT NULL, 
	origin VARCHAR(120), 
	quantity INTEGER, 
	quantity_unit VARCHAR(20) NOT NULL, 
	weight_kg FLOAT, 
	observations TEXT, 
	status VARCHAR(32) NOT NULL, 
	destination VARCHAR(32), 
	recovered_kg FLOAT, 
	waste_kg FLOAT, 
	is_demo BOOLEAN NOT NULL, 
	registered_by VARCHAR(120), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	inspected_at TIMESTAMP WITHOUT TIME ZONE, 
	decided_at TIMESTAMP WITHOUT TIME ZONE, 
	closed_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(product_id) REFERENCES products (id), 
	FOREIGN KEY(merchant_id) REFERENCES merchants (id), 
	FOREIGN KEY(area_id) REFERENCES areas (id)
);
CREATE INDEX ix_lots_is_demo ON lots (is_demo);
CREATE UNIQUE INDEX ix_lots_code ON lots (code);
CREATE INDEX ix_lots_status ON lots (status);
CREATE INDEX ix_lots_created_at ON lots (created_at);

CREATE TABLE lot_events (
	id SERIAL NOT NULL, 
	lot_id INTEGER NOT NULL, 
	type VARCHAR(30) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	detail TEXT, 
	actor VARCHAR(120), 
	from_status VARCHAR(32), 
	to_status VARCHAR(32), 
	payload JSON NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(lot_id) REFERENCES lots (id) ON DELETE CASCADE
);
CREATE INDEX ix_lot_events_created_at ON lot_events (created_at);
CREATE INDEX ix_lot_events_lot_id ON lot_events (lot_id);

CREATE TABLE lot_images (
	id SERIAL NOT NULL, 
	lot_id INTEGER NOT NULL, 
	filename VARCHAR(200) NOT NULL, 
	original_name VARCHAR(200), 
	source VARCHAR(20) NOT NULL, 
	width INTEGER NOT NULL, 
	height INTEGER NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(lot_id) REFERENCES lots (id) ON DELETE CASCADE
);
CREATE INDEX ix_lot_images_lot_id ON lot_images (lot_id);

CREATE TABLE inspections (
	id SERIAL NOT NULL, 
	lot_id INTEGER NOT NULL, 
	image_id INTEGER, 
	mode VARCHAR(10) NOT NULL, 
	scenario VARCHAR(60), 
	model_version VARCHAR(40), 
	declared_product VARCHAR(40) NOT NULL, 
	predicted_product VARCHAR(40), 
	prediction_score FLOAT, 
	quality_summary VARCHAR(20), 
	anomaly_count INTEGER NOT NULL, 
	affected_pct FLOAT, 
	incidents JSON NOT NULL, 
	result JSON NOT NULL, 
	recommendation JSON NOT NULL, 
	annotated_filename VARCHAR(200), 
	processing_ms INTEGER, 
	performed_by VARCHAR(120), 
	is_demo BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(lot_id) REFERENCES lots (id) ON DELETE CASCADE, 
	FOREIGN KEY(image_id) REFERENCES lot_images (id) ON DELETE SET NULL
);
CREATE INDEX ix_inspections_lot_id ON inspections (lot_id);
CREATE INDEX ix_inspections_created_at ON inspections (created_at);

CREATE TABLE decisions (
	id SERIAL NOT NULL, 
	lot_id INTEGER NOT NULL, 
	inspection_id INTEGER, 
	action VARCHAR(40) NOT NULL, 
	recommendation_code VARCHAR(40), 
	followed_recommendation BOOLEAN, 
	actor VARCHAR(120) NOT NULL, 
	role VARCHAR(80) NOT NULL, 
	notes TEXT, 
	kg FLOAT, 
	from_status VARCHAR(32) NOT NULL, 
	to_status VARCHAR(32) NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(lot_id) REFERENCES lots (id) ON DELETE CASCADE, 
	FOREIGN KEY(inspection_id) REFERENCES inspections (id) ON DELETE SET NULL
);
CREATE INDEX ix_decisions_created_at ON decisions (created_at);
CREATE INDEX ix_decisions_lot_id ON decisions (lot_id);
