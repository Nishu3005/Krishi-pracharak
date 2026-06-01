-- CreateTable
CREATE TABLE "uploaded_files" (
    "uploaded_file_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "original_file_name" TEXT NOT NULL,
    "upload_purpose" TEXT NOT NULL,
    "requested_csv_type" TEXT NOT NULL DEFAULT 'auto-detect',
    "detected_csv_type" TEXT NOT NULL DEFAULT 'unknown',
    "row_count" INTEGER NOT NULL DEFAULT 0,
    "status" TEXT NOT NULL DEFAULT 'uploaded',
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "data_ingestion_jobs" (
    "ingestion_job_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "uploaded_file_id" INTEGER NOT NULL,
    "requested_csv_type" TEXT NOT NULL,
    "detected_csv_type" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'mapped',
    "total_rows" INTEGER NOT NULL DEFAULT 0,
    "valid_rows" INTEGER NOT NULL DEFAULT 0,
    "invalid_rows" INTEGER NOT NULL DEFAULT 0,
    "ai_confidence" DECIMAL,
    "error_report_json" TEXT,
    "approved_at" DATETIME,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "data_ingestion_jobs_uploaded_file_id_fkey" FOREIGN KEY ("uploaded_file_id") REFERENCES "uploaded_files" ("uploaded_file_id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "schema_mappings" (
    "schema_mapping_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "ingestion_job_id" INTEGER NOT NULL,
    "source_column" TEXT NOT NULL,
    "target_table" TEXT NOT NULL,
    "target_field" TEXT NOT NULL,
    "confidence" DECIMAL,
    "required_flag" BOOLEAN NOT NULL DEFAULT false,
    "transform_note" TEXT,
    CONSTRAINT "schema_mappings_ingestion_job_id_fkey" FOREIGN KEY ("ingestion_job_id") REFERENCES "data_ingestion_jobs" ("ingestion_job_id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "staging_records" (
    "staging_record_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "ingestion_job_id" INTEGER NOT NULL,
    "row_number" INTEGER NOT NULL,
    "raw_json" TEXT NOT NULL,
    "mapped_json" TEXT NOT NULL,
    "validation_status" TEXT NOT NULL DEFAULT 'valid',
    "errors_json" TEXT,
    "ai_confidence" DECIMAL,
    "imported_flag" BOOLEAN NOT NULL DEFAULT false,
    CONSTRAINT "staging_records_ingestion_job_id_fkey" FOREIGN KEY ("ingestion_job_id") REFERENCES "data_ingestion_jobs" ("ingestion_job_id") ON DELETE RESTRICT ON UPDATE CASCADE
);
