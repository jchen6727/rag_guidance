#!/usr/bin/env bash
#
# Preflight check for scripts/setup_vertex_search.py.
#
# Verifies, in order:
#   1. gcloud CLI is installed and an account is logged in
#   2. GCP_PROJECT_ID (from .env or the environment) exists and is the active project
#   3. Billing is enabled on the project
#   4. Required APIs (Discovery Engine, Cloud Storage, Vertex AI) are enabled
#   5. The active identity holds the IAM permissions setup_vertex_search.py needs
#
# On any failure, prints the exact gcloud command(s) to fix the issue and
# continues checking the rest (so a single run surfaces every problem, not
# just the first one). Exits non-zero if any check failed.
#
# Usage:
#   scripts/preflight_check.sh
#
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

FAILURES=0
CHECK_MARK="✓"
CROSS_MARK="✗"

pass() { echo "${CHECK_MARK} $1"; }
fail() {
    echo "${CROSS_MARK} $1"
    FAILURES=$((FAILURES + 1))
}
fix() {
    echo "  Fix:"
    while IFS= read -r line; do
        echo "    ${line}"
    done <<< "$1"
    echo
}

echo "=== RAG Guidance — Vertex AI Search preflight check ==="
echo

# ---------------------------------------------------------------------------
# 0. Load .env (if present) without clobbering already-exported vars
# ---------------------------------------------------------------------------
if [[ -f "${REPO_ROOT}/.env" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${REPO_ROOT}/.env"
    set +a
fi

GCP_PROJECT_ID="${GCP_PROJECT_ID:-}"
GCP_LOCATION="${GCP_LOCATION:-global}"

# ---------------------------------------------------------------------------
# 1. gcloud CLI present and authenticated
# ---------------------------------------------------------------------------
if ! command -v gcloud >/dev/null 2>&1; then
    fail "gcloud CLI not found on PATH"
    fix "Install the Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
    echo
    echo "Cannot continue without gcloud. Aborting remaining checks."
    exit 1
fi
pass "gcloud CLI found ($(gcloud --version | head -n1))"

AUTH_LIST_OUTPUT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>&1)"
AUTH_LIST_EXIT=$?
if [[ ${AUTH_LIST_EXIT} -ne 0 ]]; then
    fail "Unable to query gcloud auth state: ${AUTH_LIST_OUTPUT}"
    fix "gcloud auth login
gcloud auth application-default login"
    ACTIVE_ACCOUNT=""
else
    ACTIVE_ACCOUNT="${AUTH_LIST_OUTPUT}"
    if [[ -z "${ACTIVE_ACCOUNT}" ]]; then
        fail "No active gcloud account"
        fix "gcloud auth login
gcloud auth application-default login"
    else
        pass "Active gcloud account: ${ACTIVE_ACCOUNT}"
    fi
fi

# Application Default Credentials are what the Python client libraries in
# setup_vertex_search.py actually use — a plain `gcloud auth login` alone
# is not sufficient.
if ! gcloud auth application-default print-access-token >/dev/null 2>&1; then
    fail "Application Default Credentials (ADC) not set up"
    fix "gcloud auth application-default login"
else
    pass "Application Default Credentials available"
fi

# ---------------------------------------------------------------------------
# 2. Project exists and matches GCP_PROJECT_ID / active gcloud config
# ---------------------------------------------------------------------------
if [[ -z "${GCP_PROJECT_ID}" ]]; then
    fail "GCP_PROJECT_ID is not set (checked .env and environment)"
    fix "cp .env.example .env   # then set GCP_PROJECT_ID=<your-project>"
    echo
    echo "Cannot continue project/billing/IAM checks without a project ID. Aborting."
    exit 1
fi

if ! gcloud projects describe "${GCP_PROJECT_ID}" --format="value(projectId)" >/dev/null 2>&1; then
    fail "Project '${GCP_PROJECT_ID}' does not exist or is not accessible to ${ACTIVE_ACCOUNT:-<no account>}"
    fix "gcloud projects list --filter=\"projectId:${GCP_PROJECT_ID}\"
# If it doesn't exist:
gcloud projects create ${GCP_PROJECT_ID}
# If it exists but isn't accessible, ask the project owner to run:
gcloud projects add-iam-policy-binding ${GCP_PROJECT_ID} \\
    --member=\"user:${ACTIVE_ACCOUNT:-YOUR_EMAIL}\" --role=\"roles/editor\""
else
    pass "Project '${GCP_PROJECT_ID}' exists and is accessible"
fi

CONFIG_GET_OUTPUT="$(gcloud config get-value project 2>&1)"
CONFIG_GET_EXIT=$?
if [[ ${CONFIG_GET_EXIT} -ne 0 ]]; then
    fail "Unable to read active gcloud config project: ${CONFIG_GET_OUTPUT}"
    fix "gcloud config set project ${GCP_PROJECT_ID}"
else
    ACTIVE_CONFIG_PROJECT="${CONFIG_GET_OUTPUT}"
    if [[ "${ACTIVE_CONFIG_PROJECT}" != "${GCP_PROJECT_ID}" ]]; then
        fail "Active gcloud config project ('${ACTIVE_CONFIG_PROJECT}') does not match GCP_PROJECT_ID ('${GCP_PROJECT_ID}')"
        fix "gcloud config set project ${GCP_PROJECT_ID}"
    else
        pass "Active gcloud config project matches GCP_PROJECT_ID"
    fi
fi

# ---------------------------------------------------------------------------
# 3. Billing enabled
# ---------------------------------------------------------------------------
BILLING_DESCRIBE_OUTPUT="$(gcloud billing projects describe "${GCP_PROJECT_ID}" \
    --format="value(billingEnabled)" 2>&1)"
BILLING_DESCRIBE_EXIT=$?
if [[ ${BILLING_DESCRIBE_EXIT} -ne 0 ]]; then
    fail "Unable to check billing status for '${GCP_PROJECT_ID}' (caller likely lacks billing.resourceAssociations.get): ${BILLING_DESCRIBE_OUTPUT}"
    fix "gcloud billing accounts list
gcloud billing projects link ${GCP_PROJECT_ID} --billing-account=<BILLING_ACCOUNT_ID>"
else
    BILLING_ENABLED="${BILLING_DESCRIBE_OUTPUT}"
    if [[ "${BILLING_ENABLED}" != "True" ]]; then
        fail "Billing is not enabled on project '${GCP_PROJECT_ID}'"
        fix "gcloud billing accounts list
gcloud billing projects link ${GCP_PROJECT_ID} --billing-account=<BILLING_ACCOUNT_ID>"
    else
        pass "Billing is enabled on '${GCP_PROJECT_ID}'"
    fi
fi

# ---------------------------------------------------------------------------
# 4. Required APIs enabled
# ---------------------------------------------------------------------------
REQUIRED_APIS=(
    "discoveryengine.googleapis.com"
    "storage.googleapis.com"
    "aiplatform.googleapis.com"
)
ENABLED_APIS="$(gcloud services list --project="${GCP_PROJECT_ID}" \
    --format="value(config.name)" 2>&1)"
SERVICES_LIST_EXIT=$?

if [[ ${SERVICES_LIST_EXIT} -ne 0 ]]; then
    fail "Unable to list enabled APIs for '${GCP_PROJECT_ID}' (gcloud services list failed)"
    fix "gcloud services list --project=${GCP_PROJECT_ID}
# Investigate the error above (e.g. missing serviceusage.services.list permission),
# then re-run this preflight check."
else
    for api in "${REQUIRED_APIS[@]}"; do
        if grep -qx "${api}" <<< "${ENABLED_APIS}"; then
            pass "API enabled: ${api}"
        else
            fail "API not enabled: ${api}"
            fix "gcloud services enable ${api} --project=${GCP_PROJECT_ID}"
        fi
    done
fi

# ---------------------------------------------------------------------------
# 5. IAM permissions required by setup_vertex_search.py
# ---------------------------------------------------------------------------
REQUIRED_PERMISSIONS=(
    "resourcemanager.projects.get"
    "serviceusage.services.list"
    "discoveryengine.dataStores.create"
    "discoveryengine.dataStores.list"
    "discoveryengine.dataStores.get"
    "discoveryengine.schemas.create"
    "discoveryengine.schemas.update"
    "discoveryengine.schemas.get"
    "discoveryengine.engines.create"
    "discoveryengine.engines.get"
)

# `gcloud projects test-iam-permissions` is not a valid gcloud command — the
# testIamPermissions RPC is only exposed via the Cloud Resource Manager REST
# API (or the google-cloud-resource-manager client library), so it is called
# directly with curl using the same ADC access token the Python code uses.
ACCESS_TOKEN="$(gcloud auth application-default print-access-token 2>/dev/null)"

if [[ -z "${ACCESS_TOKEN}" ]]; then
    fail "Cannot check IAM permissions: no Application Default Credentials access token available"
    fix "gcloud auth application-default login"
else
    PERM_JSON_ARRAY="$(printf '"%s",' "${REQUIRED_PERMISSIONS[@]}")"
    PERM_JSON_ARRAY="[${PERM_JSON_ARRAY%,}]"

    IAM_RESPONSE_FILE="$(mktemp)"
    trap 'rm -f "${IAM_RESPONSE_FILE}"' EXIT

    HTTP_STATUS="$(curl -s -o "${IAM_RESPONSE_FILE}" -w '%{http_code}' -X POST \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        "https://cloudresourcemanager.googleapis.com/v1/projects/${GCP_PROJECT_ID}:testIamPermissions" \
        -d "{\"permissions\":${PERM_JSON_ARRAY}}")"
    CURL_EXIT=$?

    if [[ ${CURL_EXIT} -ne 0 ]]; then
        fail "Unable to reach cloudresourcemanager.googleapis.com to check IAM permissions (curl exit code ${CURL_EXIT})"
        fix "Check network/proxy connectivity, then re-run: scripts/preflight_check.sh"
    elif [[ "${HTTP_STATUS}" != "200" ]]; then
        fail "IAM permission check request failed (HTTP ${HTTP_STATUS}): $(cat "${IAM_RESPONSE_FILE}")"
        fix "Verify ${ACTIVE_ACCOUNT:-the active account} has resourcemanager.projects.getIamPolicy on '${GCP_PROJECT_ID}', then re-run: scripts/preflight_check.sh"
    else
        GRANTED_PERMISSIONS="$(python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except ValueError as exc:
    sys.exit(f"invalid JSON from testIamPermissions response: {exc}")
print("\n".join(data.get("permissions", [])))
' < "${IAM_RESPONSE_FILE}")"
        PARSE_EXIT=$?

        if [[ ${PARSE_EXIT} -ne 0 ]]; then
            fail "Could not parse testIamPermissions response for '${GCP_PROJECT_ID}'"
            fix "Inspect the raw response: cat ${IAM_RESPONSE_FILE}
(this preflight check will delete that file on exit — copy it first if you need to debug)"
        else
            MISSING_PERMISSIONS=()
            for perm in "${REQUIRED_PERMISSIONS[@]}"; do
                if ! grep -qx "${perm}" <<< "${GRANTED_PERMISSIONS}"; then
                    MISSING_PERMISSIONS+=("${perm}")
                fi
            done

            if [[ ${#MISSING_PERMISSIONS[@]} -eq 0 ]]; then
                pass "IAM permissions sufficient for ${ACTIVE_ACCOUNT:-active account} to run setup_vertex_search.py"
            else
                fail "Missing IAM permission(s) for ${ACTIVE_ACCOUNT:-active account}: ${MISSING_PERMISSIONS[*]}"
                fix "gcloud projects add-iam-policy-binding ${GCP_PROJECT_ID} \\
    --member=\"user:${ACTIVE_ACCOUNT:-YOUR_EMAIL}\" --role=\"roles/discoveryengine.admin\"
gcloud projects add-iam-policy-binding ${GCP_PROJECT_ID} \\
    --member=\"user:${ACTIVE_ACCOUNT:-YOUR_EMAIL}\" --role=\"roles/serviceusage.serviceUsageViewer\""
            fi
        fi
    fi

    rm -f "${IAM_RESPONSE_FILE}"
    trap - EXIT
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "=========================================================="
if [[ ${FAILURES} -eq 0 ]]; then
    echo "${CHECK_MARK} All preflight checks passed. Safe to run:"
    echo "    PYTHONPATH=. python scripts/setup_vertex_search.py --dry-run"
    exit 0
else
    echo "${CROSS_MARK} ${FAILURES} preflight check(s) failed. Fix the issues above before running setup_vertex_search.py."
    exit 1
fi
