# Gen-AI ROI Demo: Infrastructure Setup Notebook v4
# ==================================================
# 
# This notebook sets up all the infrastructure for the Gen-AI ROI demo:
# - BigQuery dataset and tables
# - Firestore collections with seed data
# - Neo4j Aura connection and seed graph
# - Decision Trace nodes (Decision, DecisionContext, EvolutionEvent)
# - TRIGGERED_EVOLUTION relationships (THE KEY DIFFERENTIATOR)
# - CAUSED and PRECEDENT_FOR relationships (causal chains)
#
# NOTE (v4): This notebook sets up the DATA LAYER only. The agent
# implementation has been simplified to ~200 lines (agent.py + reasoning.py).
# The demo proves the ARCHITECTURE, not agent sophistication.
#
# Prerequisites:
# - GCP account with project created (gen-ai-roi-demo)
# - Billing enabled on the project
# - APIs will be enabled by this notebook
#
# Time to complete: ~35 minutes
#
# Instructions:
# 1. Run each cell in order (Shift+Enter)
# 2. Follow the prompts when asked for input
# 3. Don't skip cells - they build on each other
# 4. Green checkmarks indicate success
# 5. If a cell fails, read the error and fix before continuing
#
# Key changes from v3:
# - Added note about simplified agent architecture
# - References updated to v6 spec files
# - No changes to data seeding logic (data layer unchanged)
#
# Key changes from v2 (retained):
# - Cell 28: CAUSED and PRECEDENT_FOR relationships (Neo4j demo alignment)
# - Cell 29: Verification for causal chain relationships
# - Schema compatible with Neo4j's context-graph-demo patterns
#
# Key changes from v1 (retained):
# - Cells 27-29: Decision Trace schema (the key differentiator)
# - Cell 31: Updated summary with two-loop verification
# - Total cells: 31

# =============================================================================
# CELL 1: Install Required Packages
# =============================================================================
# This installs the Python packages we need. Run this first.
# It may take 1-2 minutes.

!pip install --quiet google-cloud-bigquery google-cloud-firestore google-cloud-aiplatform
!pip install --quiet neo4j python-dotenv

print("Ã¢Å“â€œ Packages installed successfully")

# =============================================================================
# CELL 2: Authenticate with Google Cloud
# =============================================================================
# This will open a popup asking you to sign in with your Google account.
# Sign in with the same account that owns your GCP project.

from google.colab import auth
auth.authenticate_user()

print("Ã¢Å“â€œ Authenticated with Google Cloud")

# =============================================================================
# CELL 3: Set Your Project Configuration
# =============================================================================
# IMPORTANT: Update these values to match your setup!
#
# PROJECT_ID: Your GCP project ID (e.g., "gen-ai-roi-demo" or "gen-ai-roi-demo-12345")
# REGION: Keep as us-central1 for best Vertex AI compatibility

PROJECT_ID = "gen-ai-roi-demo"  # Ã¢â€ Â CHANGE THIS to your actual project ID
REGION = "us-central1"
BIGQUERY_DATASET = "ucl"

# Don't change these
import os
os.environ["GOOGLE_CLOUD_PROJECT"] = PROJECT_ID
os.environ["GCLOUD_PROJECT"] = PROJECT_ID

print(f"Ã¢Å“â€œ Configuration set:")
print(f"  Project ID: {PROJECT_ID}")
print(f"  Region: {REGION}")
print(f"  BigQuery Dataset: {BIGQUERY_DATASET}")

# =============================================================================
# CELL 4: Enable Required GCP APIs
# =============================================================================
# This enables all the APIs we need. It may take 2-3 minutes.
# You'll see output for each API being enabled.

print("Enabling required APIs... (this takes 2-3 minutes)")
print("-" * 50)

apis = [
    "bigquery.googleapis.com",
    "firestore.googleapis.com", 
    "aiplatform.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
]

for api in apis:
    print(f"Enabling {api}...")
    !gcloud services enable {api} --project={PROJECT_ID} --quiet
    
print("-" * 50)
print("Ã¢Å“â€œ All APIs enabled successfully")

# =============================================================================
# CELL 5: Set Default Project and Region
# =============================================================================
# This configures gcloud to use your project by default.

!gcloud config set project {PROJECT_ID}
!gcloud config set compute/region {REGION}

print(f"Ã¢Å“â€œ Default project set to: {PROJECT_ID}")
print(f"Ã¢Å“â€œ Default region set to: {REGION}")

# =============================================================================
# CELL 6: Create BigQuery Dataset
# =============================================================================
# This creates the 'ucl' dataset in BigQuery.
# If it already exists, that's fine - we'll just see a message.

from google.cloud import bigquery

# Create BigQuery client
bq_client = bigquery.Client(project=PROJECT_ID)

# Create dataset
dataset_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}"
dataset = bigquery.Dataset(dataset_id)
dataset.location = "US"

try:
    dataset = bq_client.create_dataset(dataset, exists_ok=True)
    print(f"Ã¢Å“â€œ BigQuery dataset created: {dataset_id}")
except Exception as e:
    print(f"Note: {e}")
    print("If the dataset already exists, that's fine!")

# =============================================================================
# CELL 7: Create BigQuery Tables
# =============================================================================
# This creates all the tables we need for the demo.
# Tables: kpi_contracts, supply_chain_metrics, finance_metrics, invoice_exceptions

print("Creating BigQuery tables...")
print("-" * 50)

# Table 1: KPI Contracts
kpi_contracts_schema = [
    bigquery.SchemaField("kpi_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("version", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("name", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("definition", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("formula", "STRING"),
    bigquery.SchemaField("owner_email", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("grain", "STRING", mode="REPEATED"),
    bigquery.SchemaField("source_tables", "STRING", mode="REPEATED"),
    bigquery.SchemaField("join_logic", "STRING"),
    bigquery.SchemaField("filters_allowed", "STRING", mode="REPEATED"),
    bigquery.SchemaField("freshness_sla_hours", "INTEGER"),
    bigquery.SchemaField("quality_threshold", "FLOAT"),
    bigquery.SchemaField("status", "STRING"),
    bigquery.SchemaField("deprecated_by", "STRING"),
    bigquery.SchemaField("created_at", "TIMESTAMP"),
    bigquery.SchemaField("updated_at", "TIMESTAMP"),
]

table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.kpi_contracts"
table = bigquery.Table(table_id, schema=kpi_contracts_schema)
try:
    table = bq_client.create_table(table, exists_ok=True)
    print(f"Ã¢Å“â€œ Created table: kpi_contracts")
except Exception as e:
    print(f"  Note: {e}")

# Table 2: Supply Chain Metrics
supply_chain_schema = [
    bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("plant_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("plant_name", "STRING"),
    bigquery.SchemaField("region", "STRING"),
    bigquery.SchemaField("orders_total", "INTEGER"),
    bigquery.SchemaField("orders_on_time", "INTEGER"),
    bigquery.SchemaField("orders_complete", "INTEGER"),
    bigquery.SchemaField("orders_otif", "INTEGER"),
    bigquery.SchemaField("otif_pct", "FLOAT"),
    bigquery.SchemaField("otif_target", "FLOAT"),
]

table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.supply_chain_metrics"
table = bigquery.Table(table_id, schema=supply_chain_schema)
try:
    table = bq_client.create_table(table, exists_ok=True)
    print(f"Ã¢Å“â€œ Created table: supply_chain_metrics")
except Exception as e:
    print(f"  Note: {e}")

# Table 3: Finance Metrics
finance_schema = [
    bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("business_unit", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("invoices_received", "INTEGER"),
    bigquery.SchemaField("invoices_paid", "INTEGER"),
    bigquery.SchemaField("invoices_blocked", "INTEGER"),
    bigquery.SchemaField("avg_days_to_pay", "FLOAT"),
    bigquery.SchemaField("dpo", "FLOAT"),
    bigquery.SchemaField("dpo_target", "FLOAT"),
    bigquery.SchemaField("exceptions_count", "INTEGER"),
    bigquery.SchemaField("exceptions_resolved", "INTEGER"),
]

table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.finance_metrics"
table = bigquery.Table(table_id, schema=finance_schema)
try:
    table = bq_client.create_table(table, exists_ok=True)
    print(f"Ã¢Å“â€œ Created table: finance_metrics")
except Exception as e:
    print(f"  Note: {e}")

# Table 4: KPI Sprawl Registry (for duplicate detection)
sprawl_schema = [
    bigquery.SchemaField("kpi_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("similar_kpi_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("similarity_score", "FLOAT"),
    bigquery.SchemaField("dashboard_count", "INTEGER"),
    bigquery.SchemaField("estimated_annual_cost", "FLOAT"),
    bigquery.SchemaField("status", "STRING"),  # active, reviewing, consolidated
    bigquery.SchemaField("detected_at", "TIMESTAMP"),
]

table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.kpi_sprawl_registry"
table = bigquery.Table(table_id, schema=sprawl_schema)
try:
    table = bq_client.create_table(table, exists_ok=True)
    print(f"Ã¢Å“â€œ Created table: kpi_sprawl_registry")
except Exception as e:
    print(f"  Note: {e}")

print("-" * 50)
print("Ã¢Å“â€œ All BigQuery tables created successfully")

# =============================================================================
# CELL 8: Seed BigQuery with KPI Contracts
# =============================================================================
# This populates the kpi_contracts table with sample data.
# These are realistic enterprise KPIs that the demo will use.

from datetime import datetime, timedelta
import json

print("Seeding KPI contracts...")
print("-" * 50)

kpi_contracts = [
    {
        "kpi_id": "otif_weekly_by_plant",
        "version": 3,
        "name": "OTIF by Plant (Weekly)",
        "definition": "Orders delivered complete and on-time divided by total orders shipped. On-time means within promised delivery window. Complete means all line items fulfilled.",
        "formula": "COUNT(CASE WHEN on_time AND complete THEN 1 END) / COUNT(*) * 100",
        "owner_email": "supply_chain_analytics@company.com",
        "grain": ["plant_id", "week_start"],
        "source_tables": ["supply_chain.orders", "supply_chain.shipments", "supply_chain.deliveries"],
        "join_logic": "orders.order_id = shipments.order_id AND shipments.shipment_id = deliveries.shipment_id",
        "filters_allowed": ["plant_id", "region", "product_category", "customer_tier"],
        "freshness_sla_hours": 24,
        "quality_threshold": 0.95,
        "status": "active",
        "deprecated_by": None,
        "created_at": "2025-10-15T00:00:00Z",
        "updated_at": "2026-01-20T00:00:00Z",
    },
    {
        "kpi_id": "otif_plant_weekly_v1",
        "version": 1,
        "name": "OTIF Plant Weekly (Old)",
        "definition": "On-time in-full delivery rate by plant",
        "formula": "SUM(otif_flag) / COUNT(*)",
        "owner_email": "legacy_bi@company.com",
        "grain": ["plant_id", "week"],
        "source_tables": ["legacy.deliveries"],
        "join_logic": None,
        "filters_allowed": ["plant_id"],
        "freshness_sla_hours": 48,
        "quality_threshold": 0.90,
        "status": "deprecated",
        "deprecated_by": "otif_weekly_by_plant",
        "created_at": "2023-03-01T00:00:00Z",
        "updated_at": "2025-06-15T00:00:00Z",
    },
    {
        "kpi_id": "dpo_monthly",
        "version": 2,
        "name": "Days Payable Outstanding (Monthly)",
        "definition": "Average number of days to pay supplier invoices from invoice receipt date to payment date.",
        "formula": "AVG(DATEDIFF(payment_date, invoice_date))",
        "owner_email": "ap_analytics@company.com",
        "grain": ["month", "business_unit"],
        "source_tables": ["finance.invoices", "finance.payments"],
        "join_logic": "invoices.invoice_id = payments.invoice_id",
        "filters_allowed": ["vendor_id", "business_unit", "invoice_type", "vendor_tier"],
        "freshness_sla_hours": 48,
        "quality_threshold": 0.98,
        "status": "active",
        "deprecated_by": None,
        "created_at": "2025-08-10T00:00:00Z",
        "updated_at": "2026-01-18T00:00:00Z",
    },
    {
        "kpi_id": "invoice_exception_rate",
        "version": 1,
        "name": "Invoice Exception Rate",
        "definition": "Percentage of invoices that require manual intervention due to matching failures, price variances, or missing documentation.",
        "formula": "COUNT(CASE WHEN has_exception THEN 1 END) / COUNT(*) * 100",
        "owner_email": "ap_analytics@company.com",
        "grain": ["week", "exception_type"],
        "source_tables": ["finance.invoices", "finance.exceptions"],
        "join_logic": "invoices.invoice_id = exceptions.invoice_id",
        "filters_allowed": ["vendor_id", "exception_type", "business_unit"],
        "freshness_sla_hours": 24,
        "quality_threshold": 0.95,
        "status": "active",
        "deprecated_by": None,
        "created_at": "2025-11-01T00:00:00Z",
        "updated_at": "2026-01-15T00:00:00Z",
    },
    {
        "kpi_id": "first_pass_yield",
        "version": 2,
        "name": "First Pass Yield (Invoice Processing)",
        "definition": "Percentage of invoices that are processed and paid without any exceptions or manual intervention.",
        "formula": "(COUNT(*) - COUNT(exceptions)) / COUNT(*) * 100",
        "owner_email": "process_excellence@company.com",
        "grain": ["week", "vendor_tier"],
        "source_tables": ["finance.invoices", "finance.payments", "finance.exceptions"],
        "join_logic": "invoices.invoice_id = payments.invoice_id LEFT JOIN exceptions",
        "filters_allowed": ["vendor_tier", "invoice_type", "business_unit"],
        "freshness_sla_hours": 24,
        "quality_threshold": 0.95,
        "status": "active",
        "deprecated_by": None,
        "created_at": "2025-09-15T00:00:00Z",
        "updated_at": "2026-01-10T00:00:00Z",
    },
    {
        "kpi_id": "cogs_variance",
        "version": 1,
        "name": "COGS Variance to Plan",
        "definition": "Percentage variance between actual cost of goods sold and planned/budgeted COGS.",
        "formula": "(actual_cogs - planned_cogs) / planned_cogs * 100",
        "owner_email": "fp_and_a@company.com",
        "grain": ["month", "product_category"],
        "source_tables": ["finance.actuals", "finance.budget"],
        "join_logic": "actuals.period = budget.period AND actuals.category = budget.category",
        "filters_allowed": ["product_category", "region", "business_unit"],
        "freshness_sla_hours": 72,
        "quality_threshold": 0.98,
        "status": "active",
        "deprecated_by": None,
        "created_at": "2025-07-01T00:00:00Z",
        "updated_at": "2026-01-05T00:00:00Z",
    },
    {
        "kpi_id": "vendor_performance_score",
        "version": 1,
        "name": "Vendor Performance Score",
        "definition": "Composite score based on delivery performance, quality, pricing compliance, and responsiveness. Scale 0-100.",
        "formula": "0.3*delivery_score + 0.3*quality_score + 0.2*price_score + 0.2*response_score",
        "owner_email": "procurement@company.com",
        "grain": ["quarter", "vendor_id"],
        "source_tables": ["procurement.vendor_metrics", "procurement.scorecards"],
        "join_logic": "vendor_metrics.vendor_id = scorecards.vendor_id",
        "filters_allowed": ["vendor_id", "vendor_tier", "category"],
        "freshness_sla_hours": 168,
        "quality_threshold": 0.90,
        "status": "active",
        "deprecated_by": None,
        "created_at": "2025-06-01T00:00:00Z",
        "updated_at": "2026-01-08T00:00:00Z",
    },
    {
        "kpi_id": "inventory_turns",
        "version": 2,
        "name": "Inventory Turns",
        "definition": "Number of times inventory is sold and replaced over a period. Higher is generally better.",
        "formula": "cogs / average_inventory",
        "owner_email": "supply_chain_analytics@company.com",
        "grain": ["month", "warehouse_id"],
        "source_tables": ["inventory.stock_levels", "finance.cogs"],
        "join_logic": "stock_levels.period = cogs.period",
        "filters_allowed": ["warehouse_id", "product_category", "region"],
        "freshness_sla_hours": 48,
        "quality_threshold": 0.95,
        "status": "active",
        "deprecated_by": None,
        "created_at": "2025-05-01T00:00:00Z",
        "updated_at": "2025-12-20T00:00:00Z",
    },
    {
        "kpi_id": "exception_resolution_time",
        "version": 1,
        "name": "Average Exception Resolution Time",
        "definition": "Average time in hours from exception creation to resolution for invoice exceptions.",
        "formula": "AVG(TIMESTAMP_DIFF(resolved_at, created_at, HOUR))",
        "owner_email": "ap_analytics@company.com",
        "grain": ["week", "exception_type"],
        "source_tables": ["finance.exceptions"],
        "join_logic": None,
        "filters_allowed": ["exception_type", "resolution_method", "vendor_tier"],
        "freshness_sla_hours": 24,
        "quality_threshold": 0.95,
        "status": "active",
        "deprecated_by": None,
        "created_at": "2025-11-15T00:00:00Z",
        "updated_at": "2026-01-22T00:00:00Z",
    },
    {
        "kpi_id": "working_capital_days",
        "version": 1,
        "name": "Working Capital Days",
        "definition": "Days of working capital = DSO + DIO - DPO. Measures cash conversion cycle.",
        "formula": "days_sales_outstanding + days_inventory_outstanding - days_payable_outstanding",
        "owner_email": "treasury@company.com",
        "grain": ["month", "business_unit"],
        "source_tables": ["finance.ar_aging", "inventory.stock_levels", "finance.ap_aging"],
        "join_logic": "Aggregated at business unit and month level",
        "filters_allowed": ["business_unit", "region"],
        "freshness_sla_hours": 72,
        "quality_threshold": 0.98,
        "status": "active",
        "deprecated_by": None,
        "created_at": "2025-04-01T00:00:00Z",
        "updated_at": "2025-12-15T00:00:00Z",
    },
]

# Insert into BigQuery
table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.kpi_contracts"
errors = bq_client.insert_rows_json(table_id, kpi_contracts)

if errors:
    print(f"Errors inserting rows: {errors}")
else:
    print(f"Ã¢Å“â€œ Inserted {len(kpi_contracts)} KPI contracts")

# Verify
query = f"SELECT COUNT(*) as count FROM `{PROJECT_ID}.{BIGQUERY_DATASET}.kpi_contracts`"
result = bq_client.query(query).result()
for row in result:
    print(f"Ã¢Å“â€œ Verified: {row.count} KPI contracts in table")

print("-" * 50)
print("Ã¢Å“â€œ KPI contracts seeded successfully")

# =============================================================================
# CELL 9: Seed BigQuery with Supply Chain Metrics
# =============================================================================
# This creates realistic supply chain data for the past 4 weeks.
# The demo will query this data to show OTIF charts.

import random
from datetime import date, timedelta

print("Seeding supply chain metrics...")
print("-" * 50)

# Generate 4 weeks of data for 5 plants
plants = [
    {"id": "PLANT-A", "name": "Chicago Manufacturing", "region": "Midwest"},
    {"id": "PLANT-B", "name": "Atlanta Distribution", "region": "Southeast"},
    {"id": "PLANT-C", "name": "Phoenix Assembly", "region": "Southwest"},
    {"id": "PLANT-D", "name": "Seattle Fulfillment", "region": "Northwest"},
    {"id": "PLANT-E", "name": "Boston Operations", "region": "Northeast"},
]

supply_chain_data = []
base_date = date(2026, 1, 6)  # Start from 4 weeks ago

for week_offset in range(4):
    week_date = base_date + timedelta(weeks=week_offset)
    for plant in plants:
        # Generate realistic data with some variation
        orders_total = random.randint(800, 1200)
        
        # Different plants have different performance
        if plant["id"] == "PLANT-A":
            otif_rate = random.uniform(0.92, 0.96)
        elif plant["id"] == "PLANT-B":
            otif_rate = random.uniform(0.85, 0.90)
        else:
            otif_rate = random.uniform(0.88, 0.95)
        
        orders_otif = int(orders_total * otif_rate)
        orders_on_time = int(orders_total * (otif_rate + random.uniform(0.02, 0.05)))
        orders_complete = int(orders_total * (otif_rate + random.uniform(0.01, 0.04)))
        
        supply_chain_data.append({
            "date": week_date.isoformat(),
            "plant_id": plant["id"],
            "plant_name": plant["name"],
            "region": plant["region"],
            "orders_total": orders_total,
            "orders_on_time": min(orders_on_time, orders_total),
            "orders_complete": min(orders_complete, orders_total),
            "orders_otif": orders_otif,
            "otif_pct": round(otif_rate * 100, 1),
            "otif_target": 95.0,
        })

# Insert into BigQuery
table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.supply_chain_metrics"
errors = bq_client.insert_rows_json(table_id, supply_chain_data)

if errors:
    print(f"Errors: {errors}")
else:
    print(f"Ã¢Å“â€œ Inserted {len(supply_chain_data)} supply chain records")

# Verify
query = f"SELECT COUNT(*) as count FROM `{PROJECT_ID}.{BIGQUERY_DATASET}.supply_chain_metrics`"
result = bq_client.query(query).result()
for row in result:
    print(f"Ã¢Å“â€œ Verified: {row.count} supply chain records in table")

print("-" * 50)
print("Ã¢Å“â€œ Supply chain metrics seeded successfully")

# =============================================================================
# CELL 10: Seed BigQuery with Finance Metrics
# =============================================================================
# This creates finance metrics data for the demo.

print("Seeding finance metrics...")
print("-" * 50)

business_units = ["Corporate", "Retail", "Manufacturing", "Distribution"]
finance_data = []
base_date = date(2026, 1, 6)

for week_offset in range(4):
    week_date = base_date + timedelta(weeks=week_offset)
    for bu in business_units:
        invoices_received = random.randint(500, 1500)
        exception_rate = random.uniform(0.08, 0.15)
        
        invoices_blocked = int(invoices_received * exception_rate)
        invoices_paid = invoices_received - invoices_blocked - random.randint(50, 150)
        
        finance_data.append({
            "date": week_date.isoformat(),
            "business_unit": bu,
            "invoices_received": invoices_received,
            "invoices_paid": max(0, invoices_paid),
            "invoices_blocked": invoices_blocked,
            "avg_days_to_pay": round(random.uniform(25, 45), 1),
            "dpo": round(random.uniform(30, 50), 1),
            "dpo_target": 45.0,
            "exceptions_count": invoices_blocked,
            "exceptions_resolved": int(invoices_blocked * random.uniform(0.6, 0.9)),
        })

# Insert into BigQuery
table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.finance_metrics"
errors = bq_client.insert_rows_json(table_id, finance_data)

if errors:
    print(f"Errors: {errors}")
else:
    print(f"Ã¢Å“â€œ Inserted {len(finance_data)} finance records")

print("-" * 50)
print("Ã¢Å“â€œ Finance metrics seeded successfully")

# =============================================================================
# CELL 11: Seed BigQuery with Sprawl Data
# =============================================================================
# This creates the sprawl detection data - showing duplicate KPIs.
# This is key for the "democratization + governance" story.

print("Seeding sprawl detection data...")
print("-" * 50)

sprawl_data = [
    {
        "kpi_id": "otif_weekly_by_plant",
        "similar_kpi_id": "otif_plant_weekly_v1",
        "similarity_score": 0.87,
        "dashboard_count": 3,
        "estimated_annual_cost": 47000.0,
        "status": "active",
        "detected_at": "2026-01-15T00:00:00Z",
    },
    {
        "kpi_id": "dpo_monthly",
        "similar_kpi_id": "days_payable_old",
        "similarity_score": 0.82,
        "dashboard_count": 2,
        "estimated_annual_cost": 28000.0,
        "status": "reviewing",
        "detected_at": "2026-01-10T00:00:00Z",
    },
    {
        "kpi_id": "inventory_turns",
        "similar_kpi_id": "stock_rotation_legacy",
        "similarity_score": 0.79,
        "dashboard_count": 1,
        "estimated_annual_cost": 15000.0,
        "status": "consolidated",
        "detected_at": "2025-12-20T00:00:00Z",
    },
]

table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.kpi_sprawl_registry"
errors = bq_client.insert_rows_json(table_id, sprawl_data)

if errors:
    print(f"Errors: {errors}")
else:
    print(f"Ã¢Å“â€œ Inserted {len(sprawl_data)} sprawl records")

print("-" * 50)
print("Ã¢Å“â€œ Sprawl data seeded successfully")

# =============================================================================
# CELL 12: Initialize Firestore
# =============================================================================
# This sets up Firestore for operational data.
# Note: Firestore must be created in Native mode (not Datastore mode).
# If you haven't created Firestore yet, do this first:
#   1. Go to GCP Console Ã¢â€ â€™ Firestore
#   2. Click "Create Database"
#   3. Select "Native mode" (IMPORTANT!)
#   4. Select location: nam5 (United States)
#   5. Click "Create"

from google.cloud import firestore

print("Initializing Firestore...")
print("-" * 50)

try:
    db = firestore.Client(project=PROJECT_ID)
    print("Ã¢Å“â€œ Connected to Firestore")
except Exception as e:
    print(f"ERROR: {e}")
    print("")
    print("If you see a 'database not found' error:")
    print("1. Go to: https://console.cloud.google.com/firestore")
    print("2. Click 'Create Database'")
    print("3. Select 'Native mode' (NOT Datastore mode)")
    print("4. Select location: nam5")
    print("5. Click 'Create'")
    print("6. Wait 1-2 minutes, then re-run this cell")
    raise

# =============================================================================
# CELL 13: Seed Firestore with Vendors
# =============================================================================
# These are the vendors that will appear in invoice exceptions.

print("Seeding vendors...")
print("-" * 50)

vendors = [
    {
        "id": "V-8821",
        "name": "Acme Corp",
        "tier": 1,
        "relationship_years": 12,
        "reliability_score": 94.2,
        "total_spend_ytd": 2450000,
        "contract_id": "MSA-2024-0821",
        "payment_terms": "Net 30",
        "category": "Raw Materials",
    },
    {
        "id": "V-7732",
        "name": "GlobalParts Inc",
        "tier": 1,
        "relationship_years": 8,
        "reliability_score": 91.5,
        "total_spend_ytd": 1890000,
        "contract_id": "MSA-2024-0732",
        "payment_terms": "Net 30",
        "category": "Components",
    },
    {
        "id": "V-6543",
        "name": "TechSupply Co",
        "tier": 2,
        "relationship_years": 5,
        "reliability_score": 87.3,
        "total_spend_ytd": 945000,
        "contract_id": "MSA-2023-0543",
        "payment_terms": "Net 45",
        "category": "Electronics",
    },
    {
        "id": "V-5454",
        "name": "OfficeMax Solutions",
        "tier": 3,
        "relationship_years": 3,
        "reliability_score": 82.1,
        "total_spend_ytd": 320000,
        "contract_id": "PO-BLANKET-2025",
        "payment_terms": "Net 30",
        "category": "Office Supplies",
    },
    {
        "id": "V-4365",
        "name": "Pacific Logistics",
        "tier": 2,
        "relationship_years": 6,
        "reliability_score": 89.7,
        "total_spend_ytd": 1120000,
        "contract_id": "MSA-2024-0365",
        "payment_terms": "Net 15",
        "category": "Logistics",
    },
]

for vendor in vendors:
    db.collection("vendors").document(vendor["id"]).set(vendor)
    print(f"  Ã¢Å“â€œ Added vendor: {vendor['name']}")

print("-" * 50)
print(f"Ã¢Å“â€œ Seeded {len(vendors)} vendors")

# =============================================================================
# CELL 14: Seed Firestore with Contracts
# =============================================================================
# Contract terms that will be referenced in situation analysis.

print("Seeding contracts...")
print("-" * 50)

contracts = [
    {
        "id": "MSA-2024-0821",
        "vendor_id": "V-8821",
        "vendor_name": "Acme Corp",
        "type": "Master Service Agreement",
        "start_date": "2024-01-01",
        "end_date": "2026-12-31",
        "tolerance_pct": 5.0,
        "payment_terms_days": 30,
        "early_payment_discount": 2.0,
        "auto_renewal": True,
        "clauses": {
            "quantity_tolerance": "Ã‚Â±5% on all line items",
            "price_adjustment": "Annual review based on PPI",
            "quality_requirements": "ISO 9001 certified",
        },
    },
    {
        "id": "MSA-2024-0732",
        "vendor_id": "V-7732",
        "vendor_name": "GlobalParts Inc",
        "type": "Master Service Agreement",
        "start_date": "2024-03-01",
        "end_date": "2027-02-28",
        "tolerance_pct": 3.0,
        "payment_terms_days": 30,
        "early_payment_discount": 1.5,
        "auto_renewal": True,
        "clauses": {
            "quantity_tolerance": "Ã‚Â±3% on precision parts",
            "price_adjustment": "Fixed for term",
            "quality_requirements": "AS9100 certified",
        },
    },
    {
        "id": "MSA-2023-0543",
        "vendor_id": "V-6543",
        "vendor_name": "TechSupply Co",
        "type": "Master Service Agreement",
        "start_date": "2023-06-01",
        "end_date": "2026-05-31",
        "tolerance_pct": 2.0,
        "payment_terms_days": 45,
        "early_payment_discount": 0,
        "auto_renewal": False,
        "clauses": {
            "quantity_tolerance": "Ã‚Â±2% on electronic components",
            "price_adjustment": "Quarterly review",
            "quality_requirements": "RoHS compliant",
        },
    },
]

for contract in contracts:
    db.collection("contracts").document(contract["id"]).set(contract)
    print(f"  Ã¢Å“â€œ Added contract: {contract['id']}")

print("-" * 50)
print(f"Ã¢Å“â€œ Seeded {len(contracts)} contracts")

# =============================================================================
# CELL 15: Seed Firestore with Policies
# =============================================================================
# Approval policies that govern agent decisions.

print("Seeding policies...")
print("-" * 50)

policies = [
    {
        "id": "POL-AP-001",
        "name": "Auto-Approve Small Variances",
        "description": "Automatically approve invoices with variances under threshold for Tier 1 vendors",
        "conditions": {
            "vendor_tier": [1],
            "variance_pct_max": 5.0,
            "amount_max": 10000,
        },
        "action": "auto_approve",
        "requires_approval": False,
        "effective_date": "2025-01-01",
        "owner": "ap_manager@company.com",
    },
    {
        "id": "POL-AP-002",
        "name": "Manager Approval Required",
        "description": "Route to AP Manager for approval when amount exceeds threshold",
        "conditions": {
            "amount_min": 10000,
            "amount_max": 50000,
        },
        "action": "route_to_manager",
        "requires_approval": True,
        "approval_roles": ["ap_manager"],
        "effective_date": "2025-01-01",
        "owner": "ap_director@company.com",
    },
    {
        "id": "POL-AP-003",
        "name": "Tolerance-Based Auto-Approval",
        "description": "Auto-approve if variance is within contract tolerance",
        "conditions": {
            "variance_within_contract_tolerance": True,
            "vendor_tier": [1, 2],
        },
        "action": "approve_with_tolerance",
        "requires_approval": False,
        "effective_date": "2025-06-01",
        "owner": "procurement@company.com",
    },
    {
        "id": "POL-AP-004",
        "name": "Duplicate Invoice Check",
        "description": "Flag potential duplicates for manual review",
        "conditions": {
            "exception_type": "duplicate",
        },
        "action": "flag_for_review",
        "requires_approval": True,
        "approval_roles": ["ap_analyst", "ap_manager"],
        "effective_date": "2025-01-01",
        "owner": "internal_audit@company.com",
    },
    {
        "id": "POL-AP-005",
        "name": "Missing Documentation",
        "description": "Request documentation from vendor when GR is missing",
        "conditions": {
            "exception_type": "missing_gr",
        },
        "action": "request_documentation",
        "requires_approval": False,
        "auto_email_vendor": True,
        "effective_date": "2025-03-01",
        "owner": "ap_manager@company.com",
    },
]

for policy in policies:
    db.collection("policies").document(policy["id"]).set(policy)
    print(f"  Ã¢Å“â€œ Added policy: {policy['name']}")

print("-" * 50)
print(f"Ã¢Å“â€œ Seeded {len(policies)} policies")

# =============================================================================
# CELL 16: Seed Firestore with Invoice Exceptions
# =============================================================================
# These are the exceptions that will appear in the demo inbox.

print("Seeding invoice exceptions...")
print("-" * 50)

from datetime import datetime

exceptions = [
    {
        "id": "INV-4472",
        "vendor_id": "V-8821",
        "vendor_name": "Acme Corp",
        "vendor_tier": 1,
        "po_number": "PO-2026-8847",
        "po_value": 31175.00,
        "invoice_amount": 29928.00,
        "variance_amount": 1247.00,
        "variance_pct": 4.0,
        "exception_type": "three_way_match",
        "exception_reason": "Quantity variance: ordered 100, received 96",
        "ordered_qty": 100,
        "received_qty": 96,
        "contract_id": "MSA-2024-0821",
        "tolerance_pct": 5.0,
        "status": "pending",
        "priority": "medium",
        "created_at": datetime.now(),
    },
    {
        "id": "INV-4471",
        "vendor_id": "V-7732",
        "vendor_name": "GlobalParts Inc",
        "vendor_tier": 1,
        "po_number": "PO-2026-7721",
        "po_value": 84200.00,
        "invoice_amount": 84200.00,
        "variance_amount": 0,
        "variance_pct": 0,
        "exception_type": "missing_gr",
        "exception_reason": "Goods receipt not posted in system",
        "status": "pending",
        "priority": "high",
        "created_at": datetime.now(),
    },
    {
        "id": "INV-4470",
        "vendor_id": "V-6543",
        "vendor_name": "TechSupply Co",
        "vendor_tier": 2,
        "po_number": "PO-2026-6534",
        "po_value": 21000.00,
        "invoice_amount": 23100.00,
        "variance_amount": 2100.00,
        "variance_pct": 10.0,
        "exception_type": "price_variance",
        "exception_reason": "Unit price $231 vs PO price $210",
        "contract_id": "MSA-2023-0543",
        "tolerance_pct": 2.0,
        "status": "pending",
        "priority": "high",
        "created_at": datetime.now(),
    },
    {
        "id": "INV-4469",
        "vendor_id": "V-5454",
        "vendor_name": "OfficeMax Solutions",
        "vendor_tier": 3,
        "po_number": "PO-2026-5445",
        "po_value": 950.00,
        "invoice_amount": 950.00,
        "variance_amount": 0,
        "variance_pct": 0,
        "exception_type": "duplicate",
        "exception_reason": "Potential duplicate of INV-4398 (same amount, same date)",
        "status": "pending",
        "priority": "medium",
        "created_at": datetime.now(),
    },
    {
        "id": "INV-4468",
        "vendor_id": "V-8821",
        "vendor_name": "Acme Corp",
        "vendor_tier": 1,
        "po_number": "PO-2026-8832",
        "po_value": 15500.00,
        "invoice_amount": 15190.00,
        "variance_amount": 310.00,
        "variance_pct": 2.0,
        "exception_type": "three_way_match",
        "exception_reason": "Quantity variance: ordered 50, received 49",
        "ordered_qty": 50,
        "received_qty": 49,
        "contract_id": "MSA-2024-0821",
        "tolerance_pct": 5.0,
        "status": "pending",
        "priority": "low",
        "created_at": datetime.now(),
    },
]

for exc in exceptions:
    db.collection("exceptions").document(exc["id"]).set(exc)
    print(f"  Ã¢Å“â€œ Added exception: {exc['id']} ({exc['exception_type']})")

print("-" * 50)
print(f"Ã¢Å“â€œ Seeded {len(exceptions)} invoice exceptions")

# =============================================================================
# CELL 17: Seed Firestore with Agent Deployments
# =============================================================================
# This shows the versioned agent deployments for the Runtime Evolution tab.

print("Seeding agent deployments...")
print("-" * 50)

deployments = [
    {
        "id": "invoice-resolver-v2.1",
        "agent_name": "invoice-resolver",
        "version": "v2.1",
        "status": "active",
        "traffic_pct": 90,
        "created_at": datetime(2026, 1, 15),
        "eval_scores": {
            "faithfulness": 0.942,
            "tool_safety": 1.0,
            "format_compliance": 0.918,
            "policy_adherence": 0.956,
        },
        "total_runs": 847,
        "success_rate": 0.94,
    },
    {
        "id": "invoice-resolver-v2.2",
        "agent_name": "invoice-resolver",
        "version": "v2.2",
        "status": "canary",
        "traffic_pct": 10,
        "created_at": datetime(2026, 1, 25),
        "eval_scores": {
            "faithfulness": 0.918,
            "tool_safety": 1.0,
            "format_compliance": 0.891,
            "policy_adherence": 0.934,
        },
        "total_runs": 53,
        "success_rate": 0.91,
        "changes": "Improved handling of partial shipments, added commodity price check",
    },
]

for dep in deployments:
    db.collection("deployments").document(dep["id"]).set(dep)
    print(f"  Ã¢Å“â€œ Added deployment: {dep['id']} ({dep['status']}, {dep['traffic_pct']}% traffic)")

print("-" * 50)
print(f"Ã¢Å“â€œ Seeded {len(deployments)} deployments")

# =============================================================================
# CELL 18: Seed Firestore with Learned Patterns
# =============================================================================
# These patterns show what the system has "learned" over time.
# Critical for the compounding story.

print("Seeding learned patterns...")
print("-" * 50)

patterns = [
    {
        "id": "PAT-001",
        "name": "three_way_tolerance_tier1",
        "description": "3-way match variance within tolerance for Tier 1 vendors",
        "exception_type": "three_way_match",
        "conditions": {
            "vendor_tier": 1,
            "variance_pct_lte": 5.0,
            "has_contract": True,
        },
        "recommended_action": "approve_with_tolerance",
        "confidence_threshold": 0.90,
        "success_rate": 0.96,
        "occurrence_count": 23,
        "first_seen": datetime(2026, 1, 8),
        "last_seen": datetime(2026, 1, 28),
    },
    {
        "id": "PAT-002",
        "name": "missing_gr_partial_shipment",
        "description": "Missing GR due to partial shipment not yet received",
        "exception_type": "missing_gr",
        "conditions": {
            "has_partial_delivery": True,
            "delivery_in_transit": True,
        },
        "recommended_action": "wait_for_delivery",
        "confidence_threshold": 0.85,
        "success_rate": 0.88,
        "occurrence_count": 8,
        "first_seen": datetime(2026, 1, 12),
        "last_seen": datetime(2026, 1, 27),
    },
    {
        "id": "PAT-003",
        "name": "price_variance_commodity_index",
        "description": "Price variance due to commodity price fluctuation",
        "exception_type": "price_variance",
        "conditions": {
            "category": "Raw Materials",
            "commodity_price_changed": True,
        },
        "recommended_action": "verify_market_price",
        "confidence_threshold": 0.80,
        "success_rate": 0.82,
        "occurrence_count": 5,
        "first_seen": datetime(2026, 1, 18),
        "last_seen": datetime(2026, 1, 26),
    },
    {
        "id": "PAT-004",
        "name": "duplicate_same_vendor_30day",
        "description": "Duplicate invoice from same vendor within 30 days",
        "exception_type": "duplicate",
        "conditions": {
            "same_vendor": True,
            "same_amount": True,
            "days_apart_lte": 30,
        },
        "recommended_action": "flag_for_review",
        "confidence_threshold": 0.95,
        "success_rate": 1.0,
        "occurrence_count": 4,
        "first_seen": datetime(2026, 1, 10),
        "last_seen": datetime(2026, 1, 24),
    },
    {
        "id": "PAT-005",
        "name": "small_variance_auto_approve",
        "description": "Small variance under $500 for established vendors",
        "exception_type": "three_way_match",
        "conditions": {
            "variance_amount_lte": 500,
            "vendor_relationship_years_gte": 3,
        },
        "recommended_action": "auto_approve",
        "confidence_threshold": 0.92,
        "success_rate": 0.98,
        "occurrence_count": 15,
        "first_seen": datetime(2026, 1, 6),
        "last_seen": datetime(2026, 1, 28),
    },
]

for pattern in patterns:
    db.collection("patterns").document(pattern["id"]).set(pattern)
    print(f"  Ã¢Å“â€œ Added pattern: {pattern['name']} (n={pattern['occurrence_count']})")

print("-" * 50)
print(f"Ã¢Å“â€œ Seeded {len(patterns)} learned patterns")

# =============================================================================
# CELL 19: Create Sample Run Receipts
# =============================================================================
# These show what a completed agent run looks like.

print("Seeding sample receipts...")
print("-" * 50)

receipts = [
    {
        "id": "RCP-4468-20260128-091522",
        "exception_id": "INV-4468",
        "agent_version": "v2.1",
        "status": "completed",
        "created_at": datetime(2026, 1, 28, 9, 15, 22),
        
        "input_snapshot": {
            "exception_type": "three_way_match",
            "variance_amount": 310.00,
            "variance_pct": 2.0,
            "vendor_tier": 1,
        },
        
        "context_retrieved": {
            "graphs_traversed": ["vendor_master", "contract_terms", "approval_policies", "resolution_history"],
            "nodes_count": 28,
            "key_facts": [
                "Vendor Acme Corp is Tier 1 with 12-year relationship",
                "Contract MSA-2024-0821 specifies 5% tolerance",
                "7 similar exceptions auto-approved in past 30 days",
            ],
        },
        
        "decision": {
            "action": "approve_with_tolerance",
            "confidence": 0.94,
            "justification": "Variance of 2% is within the 5% tolerance specified in contract MSA-2024-0821. Vendor Acme Corp is Tier 1 with 98.2% historical approval rate for similar exceptions.",
            "pattern_matched": "PAT-001",
            "alternatives_considered": [
                {"action": "route_to_manager", "reason_rejected": "Under $10K threshold"},
                {"action": "request_credit_memo", "reason_rejected": "Within contract tolerance"},
            ],
        },
        
        "eval_scores": {
            "faithfulness": 0.94,
            "tool_safety": 1.0,
            "format_compliance": 0.92,
            "policy_adherence": 0.96,
            "overall_pass": True,
        },
        
        "execution": {
            "tools_called": [
                {"name": "get_vendor_info", "args": {"vendor_id": "V-8821"}, "result": "success"},
                {"name": "get_contract_terms", "args": {"contract_id": "MSA-2024-0821"}, "result": "success"},
                {"name": "check_tolerance", "args": {"variance_pct": 2.0, "tolerance_pct": 5.0}, "result": "within_tolerance"},
                {"name": "post_approval", "args": {"invoice_id": "INV-4468", "code": "TOL-5PCT"}, "result": "success"},
            ],
            "duration_ms": 2340,
            "verification_status": "verified",
        },
        
        "metrics": {
            "cycle_time_seconds": 2.34,
            "human_touches": 0,
            "baseline_cycle_time_hours": 4.2,
            "baseline_human_touches": 2,
        },
        
        "feedback": {
            "pattern_id": "PAT-001",
            "pattern_name": "three_way_tolerance_tier1",
            "pattern_count_before": 22,
            "pattern_count_after": 23,
        },
    },
]

for receipt in receipts:
    db.collection("receipts").document(receipt["id"]).set(receipt)
    print(f"  Ã¢Å“â€œ Added receipt: {receipt['id']}")

print("-" * 50)
print(f"Ã¢Å“â€œ Seeded {len(receipts)} receipts")

# =============================================================================
# CELL 20: Test Vertex AI (Gemini) Access
# =============================================================================
# This verifies that Gemini is accessible from your project.

print("Testing Vertex AI (Gemini) access...")
print("-" * 50)

import vertexai
from vertexai.generative_models import GenerativeModel

try:
    vertexai.init(project=PROJECT_ID, location=REGION)
    model = GenerativeModel("gemini-1.5-pro-002")
    response = model.generate_content("Say 'Gemini is ready!' and nothing else.")
    print(f"Ã¢Å“â€œ Gemini response: {response.text.strip()}")
except Exception as e:
    print(f"ERROR: {e}")
    print("")
    print("If you see a permission error:")
    print("1. Go to: https://console.cloud.google.com/vertex-ai")
    print("2. Click 'Enable API' if prompted")
    print("3. Wait 1-2 minutes, then re-run this cell")

print("-" * 50)
print("Ã¢Å“â€œ Vertex AI is ready")

# =============================================================================
# CELL 21: Neo4j Aura Setup Instructions
# =============================================================================
# Neo4j Aura is a free cloud graph database.
# This cell provides instructions - you'll create the account manually,
# then we'll connect and seed the graph.

print("""
Ã¢â€¢â€Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢â€”
Ã¢â€¢â€˜                         NEO4J AURA SETUP                                     Ã¢â€¢â€˜
Ã¢â€¢Â Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â£
Ã¢â€¢â€˜                                                                              Ã¢â€¢â€˜
Ã¢â€¢â€˜  Neo4j Aura provides a free graph database that we'll use for the           Ã¢â€¢â€˜
Ã¢â€¢â€˜  semantic graph (the "moat" visualization).                                  Ã¢â€¢â€˜
Ã¢â€¢â€˜                                                                              Ã¢â€¢â€˜
Ã¢â€¢â€˜  STEP 1: Create a Neo4j Aura Account (FREE)                                  Ã¢â€¢â€˜
Ã¢â€¢â€˜  Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬                                   Ã¢â€¢â€˜
Ã¢â€¢â€˜  1. Go to: https://neo4j.com/cloud/aura-free/                                Ã¢â€¢â€˜
Ã¢â€¢â€˜  2. Click "Start Free"                                                       Ã¢â€¢â€˜
Ã¢â€¢â€˜  3. Sign up with Google or email                                             Ã¢â€¢â€˜
Ã¢â€¢â€˜  4. Verify your email if required                                            Ã¢â€¢â€˜
Ã¢â€¢â€˜                                                                              Ã¢â€¢â€˜
Ã¢â€¢â€˜  STEP 2: Create a Free Database                                              Ã¢â€¢â€˜
Ã¢â€¢â€˜  Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬                                          Ã¢â€¢â€˜
Ã¢â€¢â€˜  1. Click "New Instance"                                                     Ã¢â€¢â€˜
Ã¢â€¢â€˜  2. Select "AuraDB Free"                                                     Ã¢â€¢â€˜
Ã¢â€¢â€˜  3. Instance name: gen-ai-roi-demo                                           Ã¢â€¢â€˜
Ã¢â€¢â€˜  4. Region: Select closest to you (or leave default)                         Ã¢â€¢â€˜
Ã¢â€¢â€˜  5. Click "Create"                                                           Ã¢â€¢â€˜
Ã¢â€¢â€˜  6. IMPORTANT: Save the password shown! You won't see it again.              Ã¢â€¢â€˜
Ã¢â€¢â€˜                                                                              Ã¢â€¢â€˜
Ã¢â€¢â€˜  STEP 3: Get Connection Details                                              Ã¢â€¢â€˜
Ã¢â€¢â€˜  Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬                                            Ã¢â€¢â€˜
Ã¢â€¢â€˜  After creation, you'll see:                                                 Ã¢â€¢â€˜
Ã¢â€¢â€˜  - Connection URI: neo4j+s://xxxxxxxx.databases.neo4j.io                     Ã¢â€¢â€˜
Ã¢â€¢â€˜  - Username: neo4j                                                           Ã¢â€¢â€˜
Ã¢â€¢â€˜  - Password: (the one you saved)                                             Ã¢â€¢â€˜
Ã¢â€¢â€˜                                                                              Ã¢â€¢â€˜
Ã¢â€¢â€˜  Enter these in the next cell.                                               Ã¢â€¢â€˜
Ã¢â€¢â€˜                                                                              Ã¢â€¢â€˜
Ã¢â€¢Å¡Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
""")

# =============================================================================
# CELL 22: Configure Neo4j Connection
# =============================================================================
# Enter your Neo4j Aura credentials here.
# These come from the Neo4j Aura console after creating your database.

# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# IMPORTANT: Fill in YOUR credentials from Neo4j Aura
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

NEO4J_URI = "neo4j+s://xxxxxxxx.databases.neo4j.io"  # Ã¢â€ Â CHANGE THIS
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "your-password-here"                 # Ã¢â€ Â CHANGE THIS

# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

print(f"Neo4j URI: {NEO4J_URI}")
print(f"Neo4j Username: {NEO4J_USERNAME}")
print(f"Neo4j Password: {'*' * len(NEO4J_PASSWORD)}")

if "xxxxxxxx" in NEO4J_URI or "your-password" in NEO4J_PASSWORD:
    print("")
    print("Ã¢Å¡Â Ã¯Â¸Â  WARNING: You haven't updated the Neo4j credentials!")
    print("   Please update NEO4J_URI and NEO4J_PASSWORD above.")
else:
    print("")
    print("Ã¢Å“â€œ Neo4j credentials configured")

# =============================================================================
# CELL 23: Connect to Neo4j
# =============================================================================
# This tests the connection to your Neo4j Aura database.

from neo4j import GraphDatabase

print("Connecting to Neo4j...")
print("-" * 50)

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    
    # Test connection
    with driver.session() as session:
        result = session.run("RETURN 'Connected!' AS message")
        record = result.single()
        print(f"Ã¢Å“â€œ {record['message']}")
        
    print("-" * 50)
    print("Ã¢Å“â€œ Neo4j connection successful")
    
except Exception as e:
    print(f"ERROR: {e}")
    print("")
    print("Common issues:")
    print("1. Wrong URI - make sure it starts with 'neo4j+s://'")
    print("2. Wrong password - use the one shown when you created the instance")
    print("3. Database still starting - wait 2-3 minutes and try again")

# =============================================================================
# CELL 24: Seed Neo4j with Entities
# =============================================================================
# This creates the semantic graph structure.
# Nodes: Vendors, Contracts, Policies, Patterns, ExceptionTypes, KPIs

print("Seeding Neo4j graph with entities...")
print("-" * 50)

def seed_neo4j_entities(tx):
    # Clear existing data (for re-runs)
    tx.run("MATCH (n) DETACH DELETE n")
    
    # Create Vendor nodes
    vendors_cypher = """
    CREATE (v1:Vendor {id: 'V-8821', name: 'Acme Corp', tier: 1, reliability_score: 94.2, relationship_years: 12})
    CREATE (v2:Vendor {id: 'V-7732', name: 'GlobalParts Inc', tier: 1, reliability_score: 91.5, relationship_years: 8})
    CREATE (v3:Vendor {id: 'V-6543', name: 'TechSupply Co', tier: 2, reliability_score: 87.3, relationship_years: 5})
    CREATE (v4:Vendor {id: 'V-5454', name: 'OfficeMax Solutions', tier: 3, reliability_score: 82.1, relationship_years: 3})
    CREATE (v5:Vendor {id: 'V-4365', name: 'Pacific Logistics', tier: 2, reliability_score: 89.7, relationship_years: 6})
    RETURN count(*) as vendors_created
    """
    result = tx.run(vendors_cypher)
    print(f"  Ã¢Å“â€œ Created Vendor nodes")
    
    # Create Contract nodes
    contracts_cypher = """
    CREATE (c1:Contract {id: 'MSA-2024-0821', tolerance_pct: 5.0, payment_terms_days: 30, type: 'MSA'})
    CREATE (c2:Contract {id: 'MSA-2024-0732', tolerance_pct: 3.0, payment_terms_days: 30, type: 'MSA'})
    CREATE (c3:Contract {id: 'MSA-2023-0543', tolerance_pct: 2.0, payment_terms_days: 45, type: 'MSA'})
    RETURN count(*) as contracts_created
    """
    tx.run(contracts_cypher)
    print(f"  Ã¢Å“â€œ Created Contract nodes")
    
    # Create Policy nodes
    policies_cypher = """
    CREATE (p1:Policy {id: 'POL-AP-001', name: 'Auto-Approve Small Variances', threshold: 5.0, action: 'auto_approve'})
    CREATE (p2:Policy {id: 'POL-AP-002', name: 'Manager Approval Required', threshold: 10000, action: 'route_to_manager'})
    CREATE (p3:Policy {id: 'POL-AP-003', name: 'Tolerance-Based Auto-Approval', action: 'approve_with_tolerance'})
    CREATE (p4:Policy {id: 'POL-AP-004', name: 'Duplicate Invoice Check', action: 'flag_for_review'})
    CREATE (p5:Policy {id: 'POL-AP-005', name: 'Missing Documentation', action: 'request_documentation'})
    RETURN count(*) as policies_created
    """
    tx.run(policies_cypher)
    print(f"  Ã¢Å“â€œ Created Policy nodes")
    
    # Create ExceptionType nodes
    exception_types_cypher = """
    CREATE (e1:ExceptionType {id: 'three_way_match', name: 'Three-Way Match Failure', description: 'PO, GR, and Invoice do not match'})
    CREATE (e2:ExceptionType {id: 'price_variance', name: 'Price Variance', description: 'Invoice price differs from PO price'})
    CREATE (e3:ExceptionType {id: 'missing_gr', name: 'Missing Goods Receipt', description: 'Invoice received but goods receipt not posted'})
    CREATE (e4:ExceptionType {id: 'duplicate', name: 'Duplicate Invoice', description: 'Potential duplicate of existing invoice'})
    RETURN count(*) as types_created
    """
    tx.run(exception_types_cypher)
    print(f"  Ã¢Å“â€œ Created ExceptionType nodes")
    
    # Create Pattern nodes (learned patterns)
    patterns_cypher = """
    CREATE (pat1:Pattern {id: 'PAT-001', name: 'three_way_tolerance_tier1', success_rate: 0.96, occurrence_count: 23})
    CREATE (pat2:Pattern {id: 'PAT-002', name: 'missing_gr_partial_shipment', success_rate: 0.88, occurrence_count: 8})
    CREATE (pat3:Pattern {id: 'PAT-003', name: 'price_variance_commodity_index', success_rate: 0.82, occurrence_count: 5})
    CREATE (pat4:Pattern {id: 'PAT-004', name: 'duplicate_same_vendor_30day', success_rate: 1.0, occurrence_count: 4})
    CREATE (pat5:Pattern {id: 'PAT-005', name: 'small_variance_auto_approve', success_rate: 0.98, occurrence_count: 15})
    RETURN count(*) as patterns_created
    """
    tx.run(patterns_cypher)
    print(f"  Ã¢Å“â€œ Created Pattern nodes")
    
    # Create KPI nodes
    kpis_cypher = """
    CREATE (k1:KPI {id: 'otif_weekly_by_plant', name: 'OTIF by Plant', version: 3, owner: 'supply_chain_analytics'})
    CREATE (k2:KPI {id: 'dpo_monthly', name: 'Days Payable Outstanding', version: 2, owner: 'ap_analytics'})
    CREATE (k3:KPI {id: 'invoice_exception_rate', name: 'Invoice Exception Rate', version: 1, owner: 'ap_analytics'})
    CREATE (k4:KPI {id: 'first_pass_yield', name: 'First Pass Yield', version: 2, owner: 'process_excellence'})
    RETURN count(*) as kpis_created
    """
    tx.run(kpis_cypher)
    print(f"  Ã¢Å“â€œ Created KPI nodes")

with driver.session() as session:
    session.execute_write(seed_neo4j_entities)

print("-" * 50)
print("Ã¢Å“â€œ Entity nodes created")

# =============================================================================
# CELL 25: Seed Neo4j with Relationships
# =============================================================================
# This creates the relationships between entities.
# These relationships are what make the graph valuable.

print("Seeding Neo4j graph with relationships...")
print("-" * 50)

def seed_neo4j_relationships(tx):
    # Vendor -> Contract relationships
    vendor_contracts = """
    MATCH (v:Vendor {id: 'V-8821'}), (c:Contract {id: 'MSA-2024-0821'})
    CREATE (v)-[:HAS_CONTRACT]->(c)
    
    WITH 1 as dummy
    MATCH (v:Vendor {id: 'V-7732'}), (c:Contract {id: 'MSA-2024-0732'})
    CREATE (v)-[:HAS_CONTRACT]->(c)
    
    WITH 1 as dummy
    MATCH (v:Vendor {id: 'V-6543'}), (c:Contract {id: 'MSA-2023-0543'})
    CREATE (v)-[:HAS_CONTRACT]->(c)
    
    RETURN count(*) as relationships
    """
    tx.run(vendor_contracts)
    print(f"  Ã¢Å“â€œ Created Vendor-Contract relationships")
    
    # Contract -> Policy relationships
    contract_policies = """
    MATCH (c:Contract {id: 'MSA-2024-0821'}), (p:Policy {id: 'POL-AP-003'})
    CREATE (c)-[:SPECIFIES_TOLERANCE {tolerance_pct: 5.0}]->(p)
    
    WITH 1 as dummy
    MATCH (c:Contract {id: 'MSA-2024-0732'}), (p:Policy {id: 'POL-AP-003'})
    CREATE (c)-[:SPECIFIES_TOLERANCE {tolerance_pct: 3.0}]->(p)
    
    RETURN count(*) as relationships
    """
    tx.run(contract_policies)
    print(f"  Ã¢Å“â€œ Created Contract-Policy relationships")
    
    # Policy -> ExceptionType relationships
    policy_exceptions = """
    MATCH (p:Policy {id: 'POL-AP-001'}), (e:ExceptionType {id: 'three_way_match'})
    CREATE (p)-[:APPLIES_TO]->(e)
    
    WITH 1 as dummy
    MATCH (p:Policy {id: 'POL-AP-003'}), (e:ExceptionType {id: 'three_way_match'})
    CREATE (p)-[:APPLIES_TO]->(e)
    
    WITH 1 as dummy
    MATCH (p:Policy {id: 'POL-AP-004'}), (e:ExceptionType {id: 'duplicate'})
    CREATE (p)-[:APPLIES_TO]->(e)
    
    WITH 1 as dummy
    MATCH (p:Policy {id: 'POL-AP-005'}), (e:ExceptionType {id: 'missing_gr'})
    CREATE (p)-[:APPLIES_TO]->(e)
    
    RETURN count(*) as relationships
    """
    tx.run(policy_exceptions)
    print(f"  Ã¢Å“â€œ Created Policy-ExceptionType relationships")
    
    # ExceptionType -> Pattern relationships (learned resolutions)
    exception_patterns = """
    MATCH (e:ExceptionType {id: 'three_way_match'}), (p:Pattern {id: 'PAT-001'})
    CREATE (e)-[:RESOLVED_BY {confidence: 0.96, occurrences: 23}]->(p)
    
    WITH 1 as dummy
    MATCH (e:ExceptionType {id: 'three_way_match'}), (p:Pattern {id: 'PAT-005'})
    CREATE (e)-[:RESOLVED_BY {confidence: 0.98, occurrences: 15}]->(p)
    
    WITH 1 as dummy
    MATCH (e:ExceptionType {id: 'missing_gr'}), (p:Pattern {id: 'PAT-002'})
    CREATE (e)-[:RESOLVED_BY {confidence: 0.88, occurrences: 8}]->(p)
    
    WITH 1 as dummy
    MATCH (e:ExceptionType {id: 'price_variance'}), (p:Pattern {id: 'PAT-003'})
    CREATE (e)-[:RESOLVED_BY {confidence: 0.82, occurrences: 5}]->(p)
    
    WITH 1 as dummy
    MATCH (e:ExceptionType {id: 'duplicate'}), (p:Pattern {id: 'PAT-004'})
    CREATE (e)-[:RESOLVED_BY {confidence: 1.0, occurrences: 4}]->(p)
    
    RETURN count(*) as relationships
    """
    tx.run(exception_patterns)
    print(f"  Ã¢Å“â€œ Created ExceptionType-Pattern relationships")
    
    # Pattern -> Policy relationships (pattern uses policy)
    pattern_policies = """
    MATCH (pat:Pattern {id: 'PAT-001'}), (pol:Policy {id: 'POL-AP-003'})
    CREATE (pat)-[:USES_POLICY]->(pol)
    
    WITH 1 as dummy
    MATCH (pat:Pattern {id: 'PAT-004'}), (pol:Policy {id: 'POL-AP-004'})
    CREATE (pat)-[:USES_POLICY]->(pol)
    
    WITH 1 as dummy
    MATCH (pat:Pattern {id: 'PAT-005'}), (pol:Policy {id: 'POL-AP-001'})
    CREATE (pat)-[:USES_POLICY]->(pol)
    
    RETURN count(*) as relationships
    """
    tx.run(pattern_policies)
    print(f"  Ã¢Å“â€œ Created Pattern-Policy relationships")
    
    # Vendor tier relationships
    vendor_patterns = """
    MATCH (v:Vendor {tier: 1}), (p:Pattern {id: 'PAT-001'})
    CREATE (v)-[:ELIGIBLE_FOR]->(p)
    
    WITH 1 as dummy
    MATCH (v:Vendor {tier: 1}), (p:Pattern {id: 'PAT-005'})
    CREATE (v)-[:ELIGIBLE_FOR]->(p)
    
    RETURN count(*) as relationships
    """
    tx.run(vendor_patterns)
    print(f"  Ã¢Å“â€œ Created Vendor-Pattern relationships")
    
    # KPI dependencies
    kpi_deps = """
    MATCH (k1:KPI {id: 'first_pass_yield'}), (k2:KPI {id: 'invoice_exception_rate'})
    CREATE (k1)-[:DEPENDS_ON]->(k2)
    
    RETURN count(*) as relationships
    """
    tx.run(kpi_deps)
    print(f"  Ã¢Å“â€œ Created KPI dependency relationships")

with driver.session() as session:
    session.execute_write(seed_neo4j_relationships)

print("-" * 50)
print("Ã¢Å“â€œ All relationships created")

# =============================================================================
# CELL 26: Verify Neo4j Graph
# =============================================================================
# This shows a summary of the graph you created.

print("Verifying Neo4j graph...")
print("-" * 50)

with driver.session() as session:
    # Count nodes by type
    result = session.run("""
        MATCH (n)
        RETURN labels(n)[0] AS type, count(*) AS count
        ORDER BY count DESC
    """)
    
    print("Nodes:")
    total_nodes = 0
    for record in result:
        print(f"  {record['type']}: {record['count']}")
        total_nodes += record['count']
    print(f"  Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬")
    print(f"  Total: {total_nodes} nodes")
    
    print("")
    
    # Count relationships by type
    result = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) AS type, count(*) AS count
        ORDER BY count DESC
    """)
    
    print("Relationships:")
    total_rels = 0
    for record in result:
        print(f"  {record['type']}: {record['count']}")
        total_rels += record['count']
    print(f"  Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬")
    print(f"  Total: {total_rels} relationships")

print("-" * 50)
print("Ã¢Å“â€œ Neo4j graph verified")

# =============================================================================

# =============================================================================
# CELL 27: â˜… NEW - Create Decision Trace Nodes
# =============================================================================
# This creates the Decision Trace entities that power THE KEY DIFFERENTIATOR:
# - Decision nodes (the decisions made by the agent)
# - DecisionContext nodes (snapshots of context at decision time)
# - EvolutionEvent nodes (agent improvements triggered by decisions)
#
# THIS IS WHAT NEO4J'S DECEMBER 2025 DEMO DOESN'T HAVE.
# Neo4j shows decision traces for better search.
# We show decision traces that also trigger agent evolution.

print("=" * 70)
print("â˜… CREATING DECISION TRACE NODES (Key Differentiator)")
print("=" * 70)
print("")

def seed_decision_trace_nodes(tx):
    """
    Creates the Decision Trace schema nodes:
    - Decision: Represents an actual decision made by the agent
    - DecisionContext: Captures the full context snapshot at decision time
    - EvolutionEvent: Represents an agent improvement triggered by a decision
    """
    
    # -------------------------------------------------------------------------
    # Decision nodes - actual decisions made by the agent
    # -------------------------------------------------------------------------
    decisions_cypher = """
    CREATE (d1:Decision {
        id: 'DEC-4468',
        type: 'auto_resolve',
        reasoning: 'Variance of 2% is within 5% tolerance. Pattern PAT-001 matched with 96% confidence.',
        confidence: 0.94,
        timestamp: datetime('2026-01-28T09:15:22Z'),
        exception_id: 'INV-4468',
        action_taken: 'approve_with_tolerance'
    })
    
    CREATE (d2:Decision {
        id: 'DEC-4469',
        type: 'escalation',
        reasoning: 'Duplicate invoice detected. Same vendor, same amount within 30 days. Requires human review.',
        confidence: 0.95,
        timestamp: datetime('2026-01-27T14:32:11Z'),
        exception_id: 'INV-4469',
        action_taken: 'flag_for_review'
    })
    
    CREATE (d3:Decision {
        id: 'DEC-4470',
        type: 'auto_resolve',
        reasoning: 'Price variance of 3.2% attributed to commodity index change. Market price verified.',
        confidence: 0.82,
        timestamp: datetime('2026-01-26T11:45:33Z'),
        exception_id: 'INV-4470',
        action_taken: 'approve_with_adjustment'
    })
    
    CREATE (d4:Decision {
        id: 'DEC-4471',
        type: 'escalation',
        reasoning: 'Missing goods receipt. Partial shipment in transit. Waiting for delivery confirmation.',
        confidence: 0.88,
        timestamp: datetime('2026-01-25T16:22:45Z'),
        exception_id: 'INV-4471',
        action_taken: 'wait_for_delivery'
    })
    
    CREATE (d5:Decision {
        id: 'DEC-4467',
        type: 'auto_resolve',
        reasoning: 'Small variance ($310) under $500 threshold. Vendor has 12-year relationship. Auto-approved.',
        confidence: 0.98,
        timestamp: datetime('2026-01-24T10:08:17Z'),
        exception_id: 'INV-4467',
        action_taken: 'auto_approve'
    })
    
    RETURN count(*) as decisions_created
    """
    tx.run(decisions_cypher)
    print(f"  âœ“ Created 5 Decision nodes")
    
    # -------------------------------------------------------------------------
    # DecisionContext nodes - capture full context at decision time
    # -------------------------------------------------------------------------
    contexts_cypher = """
    CREATE (ctx1:DecisionContext {
        id: 'CTX-4468',
        decision_id: 'DEC-4468',
        snapshot: '{"vendor_tier": 1, "contract_tolerance": 5.0, "variance_pct": 2.0}',
        inputs_gathered: ['vendor_history', 'contract_terms', 'similar_patterns', 'approval_policies'],
        policies_evaluated: ['POL-AP-001', 'POL-AP-003'],
        nodes_consulted: 28,
        graphs_traversed: ['vendor_master', 'contract_terms', 'approval_policies', 'resolution_history']
    })
    
    CREATE (ctx2:DecisionContext {
        id: 'CTX-4469',
        decision_id: 'DEC-4469',
        snapshot: '{"vendor_id": "V-5454", "amount": 950, "days_since_similar": 15}',
        inputs_gathered: ['invoice_history', 'vendor_invoices', 'duplicate_detection'],
        policies_evaluated: ['POL-AP-004'],
        nodes_consulted: 19,
        graphs_traversed: ['invoice_history', 'vendor_master']
    })
    
    CREATE (ctx3:DecisionContext {
        id: 'CTX-4470',
        decision_id: 'DEC-4470',
        snapshot: '{"variance_pct": 3.2, "commodity": "steel", "market_change_pct": 4.1}',
        inputs_gathered: ['commodity_prices', 'contract_terms', 'market_data'],
        policies_evaluated: ['POL-AP-001'],
        nodes_consulted: 22,
        graphs_traversed: ['commodity_index', 'contract_terms', 'market_data']
    })
    
    CREATE (ctx4:DecisionContext {
        id: 'CTX-4471',
        decision_id: 'DEC-4471',
        snapshot: '{"gr_status": "pending", "shipment_status": "in_transit", "eta_days": 3}',
        inputs_gathered: ['shipping_status', 'gr_records', 'vendor_delivery_history'],
        policies_evaluated: ['POL-AP-005'],
        nodes_consulted: 15,
        graphs_traversed: ['shipping_records', 'gr_history']
    })
    
    CREATE (ctx5:DecisionContext {
        id: 'CTX-4467',
        decision_id: 'DEC-4467',
        snapshot: '{"variance_amount": 310, "vendor_years": 12, "auto_threshold": 500}',
        inputs_gathered: ['vendor_history', 'auto_approve_rules'],
        policies_evaluated: ['POL-AP-001'],
        nodes_consulted: 12,
        graphs_traversed: ['vendor_master', 'approval_policies']
    })
    
    RETURN count(*) as contexts_created
    """
    tx.run(contexts_cypher)
    print(f"  âœ“ Created 5 DecisionContext nodes")
    
    # -------------------------------------------------------------------------
    # EvolutionEvent nodes - agent improvements triggered by decisions
    # THIS IS THE KEY DIFFERENTIATOR - what Neo4j doesn't have
    # -------------------------------------------------------------------------
    evolution_cypher = """
    CREATE (evo1:EvolutionEvent {
        id: 'EVO-0125',
        event_type: 'pattern_confidence',
        triggered_by: 'DEC-4468',
        before_state: '{"pattern_id": "PAT-001", "confidence": 0.92, "occurrences": 22}',
        after_state: '{"pattern_id": "PAT-001", "confidence": 0.94, "occurrences": 23}',
        description: 'Pattern PAT-001 confidence increased after successful resolution',
        timestamp: datetime('2026-01-28T09:15:25Z')
    })
    
    CREATE (evo2:EvolutionEvent {
        id: 'EVO-0126',
        event_type: 'threshold_adjustment',
        triggered_by: 'DEC-4467',
        before_state: '{"auto_approve_threshold": 400, "min_vendor_years": 5}',
        after_state: '{"auto_approve_threshold": 500, "min_vendor_years": 3}',
        description: 'Auto-approve threshold raised based on successful small variance approvals',
        timestamp: datetime('2026-01-24T10:08:20Z')
    })
    
    CREATE (evo3:EvolutionEvent {
        id: 'EVO-0127',
        event_type: 'routing_update',
        triggered_by: 'DEC-4470',
        before_state: '{"commodity_variance_handling": "manual_review"}',
        after_state: '{"commodity_variance_handling": "auto_with_market_check"}',
        description: 'Commodity price variances now auto-resolved with market verification',
        timestamp: datetime('2026-01-26T11:45:36Z')
    })
    
    RETURN count(*) as evolution_created
    """
    tx.run(evolution_cypher)
    print(f"  âœ“ Created 3 EvolutionEvent nodes")

with driver.session() as session:
    session.execute_write(seed_decision_trace_nodes)

print("")
print("-" * 70)
print("âœ“ Decision Trace nodes created (13 new nodes)")

# =============================================================================
# CELL 28: â˜… NEW - Create TRIGGERED_EVOLUTION Relationships
# =============================================================================
# This creates THE KEY RELATIONSHIP that makes our architecture different:
# 
#   (:Decision)-[:TRIGGERED_EVOLUTION]->(:EvolutionEvent)
#
# This relationship is what Neo4j's demo DOESN'T show.
# It connects decisions to agent self-improvement.
# 
# Neo4j shows: Decision â†’ Trace â†’ Graph â†’ Better Search (one loop)
# We show:    Decision â†’ Trace â†’ Graph â†’ Better Search AND Better Agent (two loops)

print("")
print("=" * 70)
print("â˜… CREATING TRIGGERED_EVOLUTION RELATIONSHIPS (The Key Differentiator)")
print("=" * 70)
print("")

def seed_decision_trace_relationships(tx):
    """
    Creates the relationships for the Decision Trace schema:
    - Decision -[:HAD_CONTEXT]-> DecisionContext
    - Decision -[:APPLIED_POLICY]-> Policy
    - Decision -[:TRIGGERED_EVOLUTION]-> EvolutionEvent  â† THE KEY RELATIONSHIP
    - Decision -[:USED_PRECEDENT]-> Decision
    """
    
    # -------------------------------------------------------------------------
    # Decision -> DecisionContext relationships
    # -------------------------------------------------------------------------
    decision_context = """
    MATCH (d:Decision {id: 'DEC-4468'}), (ctx:DecisionContext {id: 'CTX-4468'})
    CREATE (d)-[:HAD_CONTEXT]->(ctx)
    
    WITH 1 as dummy
    MATCH (d:Decision {id: 'DEC-4469'}), (ctx:DecisionContext {id: 'CTX-4469'})
    CREATE (d)-[:HAD_CONTEXT]->(ctx)
    
    WITH 1 as dummy
    MATCH (d:Decision {id: 'DEC-4470'}), (ctx:DecisionContext {id: 'CTX-4470'})
    CREATE (d)-[:HAD_CONTEXT]->(ctx)
    
    WITH 1 as dummy
    MATCH (d:Decision {id: 'DEC-4471'}), (ctx:DecisionContext {id: 'CTX-4471'})
    CREATE (d)-[:HAD_CONTEXT]->(ctx)
    
    WITH 1 as dummy
    MATCH (d:Decision {id: 'DEC-4467'}), (ctx:DecisionContext {id: 'CTX-4467'})
    CREATE (d)-[:HAD_CONTEXT]->(ctx)
    
    RETURN count(*) as relationships
    """
    tx.run(decision_context)
    print(f"  âœ“ Created Decision-DecisionContext relationships (5)")
    
    # -------------------------------------------------------------------------
    # Decision -> Policy relationships (which policies were applied)
    # -------------------------------------------------------------------------
    decision_policy = """
    MATCH (d:Decision {id: 'DEC-4468'}), (p:Policy {id: 'POL-AP-003'})
    CREATE (d)-[:APPLIED_POLICY]->(p)
    
    WITH 1 as dummy
    MATCH (d:Decision {id: 'DEC-4469'}), (p:Policy {id: 'POL-AP-004'})
    CREATE (d)-[:APPLIED_POLICY]->(p)
    
    WITH 1 as dummy
    MATCH (d:Decision {id: 'DEC-4467'}), (p:Policy {id: 'POL-AP-001'})
    CREATE (d)-[:APPLIED_POLICY]->(p)
    
    RETURN count(*) as relationships
    """
    tx.run(decision_policy)
    print(f"  âœ“ Created Decision-Policy relationships (3)")
    
    # -------------------------------------------------------------------------
    # â˜… THE KEY RELATIONSHIP â˜…
    # Decision -> EvolutionEvent (TRIGGERED_EVOLUTION)
    # This is what Neo4j's demo doesn't have!
    # -------------------------------------------------------------------------
    triggered_evolution = """
    MATCH (d:Decision {id: 'DEC-4468'}), (evo:EvolutionEvent {id: 'EVO-0125'})
    CREATE (d)-[:TRIGGERED_EVOLUTION {
        impact: 'pattern_confidence_increase',
        magnitude: 0.02,
        timestamp: datetime('2026-01-28T09:15:25Z')
    }]->(evo)
    
    WITH 1 as dummy
    MATCH (d:Decision {id: 'DEC-4467'}), (evo:EvolutionEvent {id: 'EVO-0126'})
    CREATE (d)-[:TRIGGERED_EVOLUTION {
        impact: 'threshold_raised',
        magnitude: 100,
        timestamp: datetime('2026-01-24T10:08:20Z')
    }]->(evo)
    
    WITH 1 as dummy
    MATCH (d:Decision {id: 'DEC-4470'}), (evo:EvolutionEvent {id: 'EVO-0127'})
    CREATE (d)-[:TRIGGERED_EVOLUTION {
        impact: 'routing_automated',
        magnitude: 1,
        timestamp: datetime('2026-01-26T11:45:36Z')
    }]->(evo)
    
    RETURN count(*) as relationships
    """
    tx.run(triggered_evolution)
    print(f"  âœ“ Created TRIGGERED_EVOLUTION relationships (3) â† THE KEY DIFFERENTIATOR")
    
    # -------------------------------------------------------------------------
    # Decision precedent chain (decisions that informed other decisions)
    # -------------------------------------------------------------------------
    decision_precedent = """
    MATCH (d1:Decision {id: 'DEC-4468'}), (d2:Decision {id: 'DEC-4467'})
    CREATE (d1)-[:USED_PRECEDENT {similarity: 0.89}]->(d2)
    
    RETURN count(*) as relationships
    """
    tx.run(decision_precedent)
    print(f"  âœ“ Created Decision precedent chain (1)")
    
    # -------------------------------------------------------------------------
    # NEW in v3: CAUSED relationships (align with Neo4j's causal chain pattern)
    # These relationships show how one decision caused/led to another
    # -------------------------------------------------------------------------
    caused_relationships = """
    // DEC-4467 (auto-approve under threshold) caused DEC-4468 (tolerance-based approval)
    // The threshold adjustment from DEC-4467 enabled the auto-resolve in DEC-4468
    MATCH (d1:Decision {id: 'DEC-4467'}), (d2:Decision {id: 'DEC-4468'})
    CREATE (d1)-[:CAUSED {
        reason: 'threshold_adjustment_enabled_auto_resolve',
        timestamp: datetime('2026-01-28T09:15:00Z'),
        mechanism: 'The raised threshold from DEC-4467 allowed DEC-4468 to auto-resolve'
    }]->(d2)
    
    WITH 1 as dummy
    
    // DEC-4470 (price variance with market check) influenced DEC-4471 (waiting for delivery)
    // Both involve external verification patterns
    MATCH (d1:Decision {id: 'DEC-4470'}), (d2:Decision {id: 'DEC-4471'})
    CREATE (d1)-[:CAUSED {
        reason: 'established_external_verification_pattern',
        timestamp: datetime('2026-01-26T12:00:00Z'),
        mechanism: 'Market verification pattern from DEC-4470 informed the wait-for-delivery approach'
    }]->(d2)
    
    RETURN count(*) as relationships
    """
    tx.run(caused_relationships)
    print(f"  âœ“ Created CAUSED relationships (2) â€” causal chain support")
    
    # -------------------------------------------------------------------------
    # NEW in v3: PRECEDENT_FOR relationships (align with Neo4j's precedent pattern)
    # These relationships mark decisions that serve as precedents for future decisions
    # -------------------------------------------------------------------------
    precedent_for_relationships = """
    // DEC-4467 is a precedent for DEC-4468 (similar small variance cases)
    MATCH (d1:Decision {id: 'DEC-4467'}), (d2:Decision {id: 'DEC-4468'})
    CREATE (d1)-[:PRECEDENT_FOR {
        similarity: 0.94,
        precedent_type: 'small_variance_approval',
        cited_in_reasoning: true
    }]->(d2)
    
    WITH 1 as dummy
    
    // DEC-4468 is a precedent for DEC-4470 (both auto-resolve with tolerance)
    MATCH (d1:Decision {id: 'DEC-4468'}), (d2:Decision {id: 'DEC-4470'})
    CREATE (d1)-[:PRECEDENT_FOR {
        similarity: 0.87,
        precedent_type: 'tolerance_based_approval',
        cited_in_reasoning: true
    }]->(d2)
    
    WITH 1 as dummy
    
    // DEC-4469 (duplicate detection) is a precedent for future duplicate cases
    // This establishes the pattern even though there's no subsequent duplicate yet
    MATCH (d1:Decision {id: 'DEC-4469'})
    SET d1.is_precedent = true, d1.precedent_category = 'duplicate_detection'
    
    RETURN count(*) as relationships
    """
    tx.run(precedent_for_relationships)
    print(f"  âœ“ Created PRECEDENT_FOR relationships (2) â€” precedent matching support")

with driver.session() as session:
    session.execute_write(seed_decision_trace_relationships)

print("")
print("-" * 70)
print("âœ“ Decision Trace relationships created (16 new relationships)")
print("")
print("  â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—")
print("  â•‘  TRIGGERED_EVOLUTION relationships: 3  â† THE KEY DIFFERENTIATOR  â•‘")
print("  â•‘  CAUSED relationships: 2               (causal chain support)    â•‘")
print("  â•‘  PRECEDENT_FOR relationships: 2        (precedent matching)      â•‘")
print("  â•‘                                                                   â•‘")
print("  â•‘  Schema now compatible with Neo4j's context-graph-demo patterns  â•‘")
print("  â•‘                                                                   â•‘")
print("  â•‘  Neo4j shows: Decision â†’ Trace â†’ Graph â†’ Better Search           â•‘")
print("  â•‘  We show:     Decision â†’ Trace â†’ Graph â†’ Better Search           â•‘")
print("  â•‘                                      â””â”€â”€â†’ Better Agent (EVO)     â•‘")
print("  â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•")

# =============================================================================
# CELL 29: â˜… NEW - Verify Two-Loop Schema (UPDATED v3)
# =============================================================================
# This verifies that the Decision Trace schema is correctly set up.
# The TRIGGERED_EVOLUTION count must be > 0 for the demo to work.
#
# Expected counts (v3):
# - Decision nodes: 5
# - DecisionContext nodes: 5
# - EvolutionEvent nodes: 3
# - TRIGGERED_EVOLUTION relationships: 3 (CRITICAL!)
# - CAUSED relationships: 2 (causal chain support)
# - PRECEDENT_FOR relationships: 2 (precedent matching)

print("")
print("=" * 70)
print("â˜… VERIFYING TWO-LOOP SCHEMA (v3)")
print("=" * 70)
print("")

with driver.session() as session:
    # Count all node types including new ones
    result = session.run("""
        MATCH (n)
        RETURN labels(n)[0] AS type, count(*) AS count
        ORDER BY count DESC
    """)
    
    print("Decision Trace Schema Verification:")
    print("-" * 50)
    
    total_nodes = 0
    decision_count = 0
    context_count = 0
    evolution_count = 0
    
    for record in result:
        node_type = record['type']
        count = record['count']
        total_nodes += count
        
        if node_type == 'Decision':
            decision_count = count
            print(f"  Decision nodes:           {count}")
        elif node_type == 'DecisionContext':
            context_count = count
            print(f"  DecisionContext nodes:    {count}")
        elif node_type == 'EvolutionEvent':
            evolution_count = count
            print(f"  EvolutionEvent nodes:     {count}")
    
    # Count TRIGGERED_EVOLUTION relationships (the key metric)
    result = session.run("""
        MATCH ()-[r:TRIGGERED_EVOLUTION]->()
        RETURN count(r) as count
    """)
    triggered_count = result.single()['count']
    print(f"  TRIGGERED_EVOLUTION rels: {triggered_count}  â† THE KEY RELATIONSHIP")
    
    # NEW in v3: Count CAUSED relationships
    result = session.run("""
        MATCH ()-[r:CAUSED]->()
        RETURN count(r) as count
    """)
    caused_count = result.single()['count']
    print(f"  CAUSED rels:              {caused_count}  (causal chains)")
    
    # NEW in v3: Count PRECEDENT_FOR relationships
    result = session.run("""
        MATCH ()-[r:PRECEDENT_FOR]->()
        RETURN count(r) as count
    """)
    precedent_count = result.single()['count']
    print(f"  PRECEDENT_FOR rels:       {precedent_count}  (precedent matching)")
    
    print("")
    print(f"  Total nodes: {total_nodes}")
    
    # Count all relationships
    result = session.run("""
        MATCH ()-[r]->()
        RETURN count(r) as count
    """)
    total_rels = result.single()['count']
    print(f"  Total relationships: {total_rels}")
    
    print("")
    print("-" * 50)
    
    # Verification check (updated for v3)
    if triggered_count > 0 and decision_count > 0 and evolution_count > 0:
        print("âœ“ Two-loop schema verified â€” TRIGGERED_EVOLUTION relationships exist")
        print("")
        if caused_count > 0 and precedent_count > 0:
            print("âœ“ Neo4j compatibility verified â€” CAUSED and PRECEDENT_FOR exist")
            print("  Schema is compatible with Neo4j's context-graph-demo patterns")
        print("")
        print("  The demo can now show:")
        print("  â€¢ Decision traces accumulating (Loop 1: Better Search)")
        print("  â€¢ Evolution events triggered (Loop 2: Better Agent)")
        print("  â€¢ Causal chains between decisions (Neo4j demo alignment)")
        print("  â€¢ Precedent matching for similar decisions")
        print("  â€¢ \"Neo4j's agent gets better data. Our agent becomes a better agent.\"")
    else:
        print("âœ— ERROR: Two-loop schema incomplete!")
        print(f"  Decision nodes: {decision_count} (need > 0)")
        print(f"  EvolutionEvent nodes: {evolution_count} (need > 0)")
        print(f"  TRIGGERED_EVOLUTION rels: {triggered_count} (need > 0)")
        print("")
        print("  Re-run Cells 27 and 28 to fix this.")

# =============================================================================
# CELL 30: Save Configuration for Local Development
# =============================================================================
# This creates a .env file content that you can use locally.

print("=" * 70)
print("CONFIGURATION FOR LOCAL DEVELOPMENT")
print("=" * 70)
print("")
print("Copy this to your .env file in gen-ai-roi-demo/:")
print("")
print("-" * 70)
env_content = f"""# GCP Configuration
GOOGLE_CLOUD_PROJECT={PROJECT_ID}
GOOGLE_CLOUD_REGION={REGION}

# BigQuery
BIGQUERY_DATASET={BIGQUERY_DATASET}

# Vertex AI (Gemini)
GEMINI_MODEL=gemini-1.5-pro-002
GEMINI_LOCATION={REGION}

# Neo4j Aura
NEO4J_URI={NEO4J_URI}
NEO4J_USERNAME={NEO4J_USERNAME}
NEO4J_PASSWORD={NEO4J_PASSWORD}

# Application
LOG_LEVEL=INFO
ENVIRONMENT=development
"""
print(env_content)
print("-" * 70)

# =============================================================================
# =============================================================================
# CELL 31: Final Summary (v3)
# =============================================================================
# This summary reflects the v3 notebook with Neo4j-compatible schema.

print("""
================================================================================
                         SETUP COMPLETE! (v3)
================================================================================

What was created:
-----------------

BigQuery (ucl dataset):
  * kpi_contracts (10 KPIs with definitions, owners, etc.)
  * supply_chain_metrics (4 weeks of OTIF data)
  * finance_metrics (4 weeks of DPO/invoice data)
  * kpi_sprawl_registry (duplicate KPI detection data)

Firestore (Native mode):
  * vendors (5 vendors with tiers and reliability scores)
  * contracts (3 contracts with tolerance terms)
  * policies (5 approval policies)
  * exceptions (5 invoice exceptions for demo)
  * deployments (2 agent versions: active + canary)
  * patterns (5 learned patterns)
  * receipts (1 sample run receipt)

Neo4j Aura (semantic graph):
  * ~39 nodes (Vendors, Contracts, Policies, Patterns, KPIs, Decision Trace)
  * ~35 relationships (includes new CAUSED and PRECEDENT_FOR)

Decision Trace Schema (THE KEY DIFFERENTIATOR):
  * 5 Decision nodes (actual decisions made by agent)
  * 5 DecisionContext nodes (snapshots at decision time)
  * 3 EvolutionEvent nodes (agent improvements)
  * 3 TRIGGERED_EVOLUTION relationships  <-- THE KEY ADDITION

NEW in v3 - Neo4j Compatibility (causal chains):
  * 2 CAUSED relationships (causal chain support)
  * 2 PRECEDENT_FOR relationships (precedent matching)
  * Schema compatible with github.com/johnymontana/context-graph-demo

Vertex AI:
  * Gemini 1.5 Pro accessible

================================================================================
The Two Loops Are Ready:
================================================================================

  Loop 1 (Situation Analyzer):
    Decision --> Trace --> Graph --> Better Search
                                 --> Causal Chain (CAUSED)
                                 --> Precedents (PRECEDENT_FOR)

  Loop 2 (Runtime Evolution):
    Decision --> Trace --> Graph --> Better Agent
                                       ^
                            TRIGGERED_EVOLUTION

  "Neo4j's agent gets better data. Our agent becomes a better agent."

================================================================================
Schema Comparison with Neo4j Demo:
================================================================================

  Neo4j context-graph-demo has:
    (:Decision)-[:CAUSED]->(:Decision)           âœ“ We have this
    (:Decision)-[:PRECEDENT_FOR]->(:Decision)    âœ“ We have this
    (:Decision)-[:APPLIED_POLICY]->(:Policy)     âœ“ We have this

  We ALSO have (our differentiator):
    (:Decision)-[:TRIGGERED_EVOLUTION]->(:EvolutionEvent)  â˜… UNIQUE

================================================================================

Next Steps:
-----------
  1. Copy the .env content from the previous cell
  2. Return to your local machine
  3. Continue with bootstrap sequence (Phase 6: Local Environment)
  4. Start building with Claude Code!

Reference: Neo4j's context-graph-demo
  https://github.com/johnymontana/context-graph-demo

================================================================================
""")
