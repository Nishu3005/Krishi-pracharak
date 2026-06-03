-- AlterTable
ALTER TABLE "data_ingestion_jobs" ADD COLUMN "ai_provider" TEXT;
ALTER TABLE "data_ingestion_jobs" ADD COLUMN "ai_model" TEXT;
ALTER TABLE "data_ingestion_jobs" ADD COLUMN "reasoning_summary" TEXT;
ALTER TABLE "data_ingestion_jobs" ADD COLUMN "data_quality_warnings_json" TEXT;
ALTER TABLE "data_ingestion_jobs" ADD COLUMN "suggested_fixes_json" TEXT;
ALTER TABLE "data_ingestion_jobs" ADD COLUMN "import_recommendation" TEXT;

-- CreateTable
CREATE TABLE "validation_errors" (
    "validation_error_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "ingestion_job_id" INTEGER NOT NULL,
    "staging_record_id" INTEGER,
    "row_number" INTEGER NOT NULL,
    "column_name" TEXT,
    "error_type" TEXT NOT NULL,
    "severity" TEXT NOT NULL,
    "error_message" TEXT NOT NULL,
    "suggested_fix" TEXT,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "validation_errors_ingestion_job_id_fkey" FOREIGN KEY ("ingestion_job_id") REFERENCES "data_ingestion_jobs" ("ingestion_job_id") ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT "validation_errors_staging_record_id_fkey" FOREIGN KEY ("staging_record_id") REFERENCES "staging_records" ("staging_record_id") ON DELETE SET NULL ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "ai_generation_logs" (
    "ai_generation_log_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "feature" TEXT NOT NULL,
    "provider" TEXT NOT NULL,
    "model" TEXT NOT NULL,
    "input_summary" TEXT NOT NULL,
    "output_summary" TEXT,
    "status" TEXT NOT NULL,
    "error_message" TEXT,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
