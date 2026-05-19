pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '3'))
  }

  parameters {
    choice(
      name: 'PROVIDER_SCOPE',
      choices: [
        'release_chain',
        'big_two_1of2',
        'big_two_2of2',
        'rtk_megafon',
        'small_pool',
        'mts',
        'beeline',
        'megafon',
        't2',
        'rostelecom',
        'domru',
        'ttk',
      ],
      description: 'URL-brand scope. release_chain: big_two 1/2 -> big_two 2/2 -> rtk_megafon -> small_pool(domru+ttk).'
    )
    string(name: 'SITE', defaultValue: '', description: 'Unused in URL-brand mode. Keep empty.')
    choice(name: 'FORM_SUITE', choices: ['all', 'profit', 'connection', 'connection_cards', 'checkaddress', 'business', 'undecided', 'moving', 'express'], description: 'Form suite to run in URL-brand mode.')
    choice(name: 'SERVICE_MODE', choices: ['core', 'variants', 'all'], description: 'Service mode to run.')
    booleanParam(name: 'ENABLE_CONTINUOUS_LOOP', defaultValue: false, description: 'After summary, schedule next build with same params.')
    string(name: 'LOOP_DELAY_SECONDS', defaultValue: '60', description: 'Delay before scheduling next loop build.')
    string(name: 'CHAIN_NEXT_JOB', defaultValue: '', description: 'Optional: next Jenkins job name for chained 24/7 run.')
    string(name: 'CHAIN_NEXT_SCOPE', defaultValue: '', description: 'Optional: PROVIDER_SCOPE value for next chained job.')
    booleanParam(name: 'ENABLE_PERIODIC_ARTIFACT_PURGE', defaultValue: true, description: 'Every N builds, delete archived artifacts/allure reports of previous builds for this job.')
    string(name: 'PERIODIC_PURGE_EVERY', defaultValue: '5', description: 'Run full artifact purge every N-th build (integer >= 2).')

    booleanParam(name: 'RUN_CHROMIUM', defaultValue: true, description: 'Run desktop chromium profile.')
    booleanParam(name: 'RUN_FIREFOX', defaultValue: false, description: 'Run desktop firefox profile.')
    booleanParam(name: 'RUN_WEBKIT', defaultValue: false, description: 'Run desktop webkit profile.')
    booleanParam(name: 'RUN_MOBILE_CHROMIUM', defaultValue: false, description: 'Run mobile chromium profile.')
    booleanParam(name: 'RUN_MOBILE_WEBKIT', defaultValue: false, description: 'Run mobile webkit profile.')

    choice(name: 'BLOCKING_PROFILE', choices: ['none', 'adblock-mvp'], description: 'Blocking profile.')
    booleanParam(name: 'ALERT_ERRORS', defaultValue: true, description: 'Enable single-site error alerts in pytest runtime.')
    booleanParam(name: 'ALERT_AGGREGATES', defaultValue: true, description: 'Enable aggregate alerts in pytest runtime.')
    booleanParam(name: 'ALERT_SUMMARY', defaultValue: true, description: 'Enable summary alerts in pytest runtime.')
    booleanParam(name: 'ALERT_RECOVERED', defaultValue: true, description: 'Enable recovered alerts in pytest runtime.')
    booleanParam(name: 'USE_TELEGRAM_PROXY', defaultValue: true, description: 'Use Jenkins proxy credentials for Telegram alerts.')
  }

  environment {
    PLAYWRIGHT_BROWSERS_PATH = '/var/lib/jenkins/cache/ms-playwright'
    PIP_CACHE_DIR = '/var/lib/jenkins/cache/pip'
    PIP_DISABLE_PIP_VERSION_CHECK = '1'
    PYTHONUNBUFFERED = '1'
    PW_VIDEO_DIR = 'artifacts/videos'
    PYTHON_BIN = '.venv/bin/python'
    PYTHON_BIN_FILE = '.python_bin'
    REQ_HASH_FILE = '.requirements.sha256'
    ALERT_ERRORS_ENABLED = "${params.ALERT_ERRORS}"
    ALERT_AGGREGATES_ENABLED = "${params.ALERT_AGGREGATES}"
    ALERT_SUMMARY_ENABLED = "${params.ALERT_SUMMARY}"
    ALERT_RECOVERED_ENABLED = "${params.ALERT_RECOVERED}"
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Validate parameters') {
      steps {
        script {
          if (!(params.RUN_CHROMIUM || params.RUN_FIREFOX || params.RUN_WEBKIT || params.RUN_MOBILE_CHROMIUM || params.RUN_MOBILE_WEBKIT)) {
            error('Select at least one browser/profile toggle.')
          }
          if ((params.SITE ?: '').trim()) {
            error('SITE parameter is not supported in URL-brand mode. Leave SITE empty.')
          }
          if ((params.LOOP_DELAY_SECONDS ?: '').trim() && !((params.LOOP_DELAY_SECONDS as String) ==~ /\d+/)) {
            error('LOOP_DELAY_SECONDS must be an integer >= 0.')
          }
          if ((params.PERIODIC_PURGE_EVERY ?: '').trim() && !((params.PERIODIC_PURGE_EVERY as String) ==~ /\d+/)) {
            error('PERIODIC_PURGE_EVERY must be an integer >= 2.')
          }
        }
      }
    }

    stage('Cache diagnostics') {
      steps {
        sh '''
          set -e
          echo "=== Cache diagnostics ==="
          echo "Workspace: $(pwd)"

          if [ -x ".venv/bin/python" ]; then
            echo "[VENV] Reused: .venv exists"
            .venv/bin/python --version || true
          else
            echo "[VENV] Missing: .venv will be created"
          fi

          if [ -f ".requirements.sha256" ]; then
            echo "[REQ_HASH] Found: $(cat .requirements.sha256)"
          else
            echo "[REQ_HASH] Missing: deps install expected"
          fi

          if [ -d "${PIP_CACHE_DIR}" ]; then
            echo "[PIP_CACHE] Found: ${PIP_CACHE_DIR}"
            du -sh "${PIP_CACHE_DIR}" || true
          else
            echo "[PIP_CACHE] Missing: ${PIP_CACHE_DIR}"
          fi

          if [ -d "${PLAYWRIGHT_BROWSERS_PATH}" ]; then
            echo "[PW_CACHE] Found: ${PLAYWRIGHT_BROWSERS_PATH}"
            ls -1 "${PLAYWRIGHT_BROWSERS_PATH}" || true
          else
            echo "[PW_CACHE] Missing: ${PLAYWRIGHT_BROWSERS_PATH}"
          fi
          echo "========================="
        '''
      }
    }

    stage('Prepare Python') {
      steps {
        sh '''
          set -e
          python3 --version
          mkdir -p "${PIP_CACHE_DIR}"
          pybin="${PYTHON_BIN}"

          if [ ! -x "${pybin}" ]; then
            python3 -m venv .venv || true
          fi

          if [ ! -x "${pybin}" ]; then
            python3 -m ensurepip --upgrade || true
            python3 -m venv .venv || true
          fi

          if [ ! -x "${pybin}" ]; then
            if ! python3 -m pip --version >/dev/null 2>&1; then
              if ! python3 -m ensurepip --upgrade >/dev/null 2>&1; then
                curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
                python3 /tmp/get-pip.py --user
              fi
            fi
            pybin="python3"
          fi

          echo "${pybin}" > "${PYTHON_BIN_FILE}"
          "${pybin}" --version

          current_hash="$(sha256sum requirements.txt | awk '{print $1}')"
          saved_hash=""
          if [ -f "${REQ_HASH_FILE}" ]; then
            saved_hash="$(cat "${REQ_HASH_FILE}")"
          fi

          need_install=0
          if [ ! -f "${REQ_HASH_FILE}" ]; then
            need_install=1
          fi
          if [ "${current_hash}" != "${saved_hash}" ]; then
            need_install=1
          fi
          if ! "${pybin}" -m pytest --version >/dev/null 2>&1; then
            need_install=1
          fi

          if [ "${need_install}" = "1" ]; then
            echo "Installing Python dependencies (first run or requirements changed)..."
            "${pybin}" -m pip install --cache-dir "${PIP_CACHE_DIR}" --upgrade pip
            "${pybin}" -m pip install --cache-dir "${PIP_CACHE_DIR}" -r requirements.txt
            echo "${current_hash}" > "${REQ_HASH_FILE}"
          else
            echo "Python dependencies already installed, skip pip install."
          fi
        '''
      }
    }

    stage('Prepare Playwright cache') {
      steps {
        sh '''
          set -e
          mkdir -p "${PLAYWRIGHT_BROWSERS_PATH}"
          echo "PLAYWRIGHT_BROWSERS_PATH=${PLAYWRIGHT_BROWSERS_PATH}"
          ls -la "${PLAYWRIGHT_BROWSERS_PATH}" || true
        '''
      }
    }

    stage('Install missing Playwright browsers') {
      steps {
        sh '''
          set -e
          pybin="$(cat "${PYTHON_BIN_FILE}")"
          need_chromium=0
          need_firefox=0
          need_webkit=0

          if [ "${RUN_CHROMIUM}" = "true" ] || [ "${RUN_MOBILE_CHROMIUM}" = "true" ]; then
            need_chromium=1
          fi
          if [ "${RUN_FIREFOX}" = "true" ]; then
            need_firefox=1
          fi
          if [ "${RUN_WEBKIT}" = "true" ] || [ "${RUN_MOBILE_WEBKIT}" = "true" ]; then
            need_webkit=1
          fi

          if [ "${need_chromium}" = "1" ]; then
            if ls "${PLAYWRIGHT_BROWSERS_PATH}"/chromium-* >/dev/null 2>&1; then
              echo "Chromium already exists in shared cache."
            else
              "${pybin}" -m playwright install chromium
            fi
          fi

          if [ "${need_firefox}" = "1" ]; then
            if ls "${PLAYWRIGHT_BROWSERS_PATH}"/firefox-* >/dev/null 2>&1; then
              echo "Firefox already exists in shared cache."
            else
              "${pybin}" -m playwright install firefox
            fi
          fi

          if [ "${need_webkit}" = "1" ]; then
            if ls "${PLAYWRIGHT_BROWSERS_PATH}"/webkit-* >/dev/null 2>&1; then
              echo "WebKit already exists in shared cache."
            else
              "${pybin}" -m playwright install webkit
            fi
          fi
        '''
      }
    }

    stage('Run provider matrix') {
      steps {
        script {
          def runMatrix = {
            sh '''
          set -e
          pybin="$(cat "${PYTHON_BIN_FILE}")"

          rm -rf allure-results allure-results-* || true
          mkdir -p allure-results

          suites=""
          if [ "${FORM_SUITE}" = "all" ]; then
            suites="profit connection connection_cards checkaddress business undecided moving express"
          else
            suites="${FORM_SUITE}"
          fi

          run_one() {
            brand="$1"
            mode="$2"
            browser="$3"
            profile="$4"
            suffix="$5"
            shard_index="$6"
            shard_total="$7"
            suite="$8"

            PYTEST_ARGS="big_landing_code.py --alluredir=allure-results-${mode}-${suffix}-${brand}-${suite}-s${shard_index}of${shard_total} --timeout=600 -s --service-mode=${mode} --browser=${browser} --blocking-profile=${BLOCKING_PROFILE} --url-brand=${brand} --form-suite=${suite} --url-shard-index=${shard_index} --url-shard-total=${shard_total}"
            if [ -n "${profile}" ]; then
              PYTEST_ARGS="${PYTEST_ARGS} --execution-profile=${profile}"
            fi

            echo "Running: brand=${brand} suite=${suite} shard=${shard_index}/${shard_total} mode=${mode} browser=${browser} profile=${profile:-desktop}"
            echo "Pytest args: ${PYTEST_ARGS}"
            "${pybin}" -m pytest ${PYTEST_ARGS}
          }

          run_brand_shard() {
            brand="$1"
            shard_index="$2"
            shard_total="$3"
            echo "==================================================="
            echo "Brand: ${brand} | shard ${shard_index}/${shard_total}"
            echo "==================================================="

            for suite in ${suites}; do
              if [ "${RUN_CHROMIUM}" = "true" ]; then
                if [ "${SERVICE_MODE}" = "core" ] || [ "${SERVICE_MODE}" = "all" ]; then
                  run_one "${brand}" "core" "chromium" "" "chromium" "${shard_index}" "${shard_total}" "${suite}"
                fi
                if [ "${SERVICE_MODE}" = "variants" ] || [ "${SERVICE_MODE}" = "all" ]; then
                  run_one "${brand}" "variants" "chromium" "" "chromium" "${shard_index}" "${shard_total}" "${suite}"
                fi
              fi

              if [ "${RUN_FIREFOX}" = "true" ]; then
                if [ "${SERVICE_MODE}" = "core" ] || [ "${SERVICE_MODE}" = "all" ]; then
                  run_one "${brand}" "core" "firefox" "" "firefox" "${shard_index}" "${shard_total}" "${suite}"
                fi
                if [ "${SERVICE_MODE}" = "variants" ] || [ "${SERVICE_MODE}" = "all" ]; then
                  run_one "${brand}" "variants" "firefox" "" "firefox" "${shard_index}" "${shard_total}" "${suite}"
                fi
              fi

              if [ "${RUN_WEBKIT}" = "true" ]; then
                if [ "${SERVICE_MODE}" = "core" ] || [ "${SERVICE_MODE}" = "all" ]; then
                  run_one "${brand}" "core" "webkit" "" "webkit" "${shard_index}" "${shard_total}" "${suite}"
                fi
                if [ "${SERVICE_MODE}" = "variants" ] || [ "${SERVICE_MODE}" = "all" ]; then
                  run_one "${brand}" "variants" "webkit" "" "webkit" "${shard_index}" "${shard_total}" "${suite}"
                fi
              fi

              if [ "${RUN_MOBILE_CHROMIUM}" = "true" ]; then
                if [ "${SERVICE_MODE}" = "core" ] || [ "${SERVICE_MODE}" = "all" ]; then
                  run_one "${brand}" "core" "chromium" "mobile-chromium" "mobile-chromium" "${shard_index}" "${shard_total}" "${suite}"
                fi
                if [ "${SERVICE_MODE}" = "variants" ] || [ "${SERVICE_MODE}" = "all" ]; then
                  run_one "${brand}" "variants" "chromium" "mobile-chromium" "mobile-chromium" "${shard_index}" "${shard_total}" "${suite}"
                fi
              fi

              if [ "${RUN_MOBILE_WEBKIT}" = "true" ]; then
                if [ "${SERVICE_MODE}" = "core" ] || [ "${SERVICE_MODE}" = "all" ]; then
                  run_one "${brand}" "core" "webkit" "mobile-webkit" "mobile-webkit" "${shard_index}" "${shard_total}" "${suite}"
                fi
                if [ "${SERVICE_MODE}" = "variants" ] || [ "${SERVICE_MODE}" = "all" ]; then
                  run_one "${brand}" "variants" "webkit" "mobile-webkit" "mobile-webkit" "${shard_index}" "${shard_total}" "${suite}"
                fi
              fi
            done
          }

          run_scope() {
            scope_name="$1"
            echo "###################################################"
            echo "SCOPE: ${scope_name}"
            echo "###################################################"
            case "${scope_name}" in
              big_two_1of2)
                run_brand_shard "mts" "1" "2"
                run_brand_shard "beeline" "1" "2"
                ;;
              big_two_2of2)
                run_brand_shard "mts" "2" "2"
                run_brand_shard "beeline" "2" "2"
                ;;
              rtk_megafon)
                run_brand_shard "rostelecom" "1" "1"
                run_brand_shard "megafon" "1" "1"
                ;;
              small_pool)
                run_brand_shard "domru" "1" "1"
                run_brand_shard "ttk" "1" "1"
                ;;
              mts|beeline|megafon|t2|rostelecom|domru|ttk)
                run_brand_shard "${scope_name}" "1" "1"
                ;;
              *)
                echo "Unknown PROVIDER_SCOPE: ${scope_name}"
                exit 2
                ;;
            esac
          }

          if [ "${PROVIDER_SCOPE}" = "release_chain" ]; then
            run_scope "big_two_1of2"
            run_scope "big_two_2of2"
            run_scope "rtk_megafon"
            run_scope "small_pool"
          else
            run_scope "${PROVIDER_SCOPE}"
          fi

          for d in allure-results-*; do
            if [ -d "${d}" ]; then
              cp -R "${d}"/. allure-results/
            fi
          done
        '''
          }

          if (params.USE_TELEGRAM_PROXY) {
            withCredentials([
              string(credentialsId: 'telegram_proxy_url', variable: 'TELEGRAM_PROXY_URL'),
              string(credentialsId: 'telegram_proxy_auth_secret', variable: 'TELEGRAM_PROXY_AUTH_SECRET'),
              string(credentialsId: 'telegram_proxy_global_test', variable: 'TELEGRAM_PROXY_CREDS')
            ]) {
              echo 'Telegram proxy credentials loaded from Jenkins credentials store.'
              runMatrix()
            }
          } else {
            echo 'Telegram proxy disabled by parameter.'
            runMatrix()
          }
        }
      }
    }
  }

  post {
    always {
      sh '''
        set +e
        mkdir -p allure-results
        for d in allure-results-*; do
          if [ -d "${d}" ]; then
            cp -R "${d}"/. allure-results/
          fi
        done
        exit 0
      '''
      script {
        def isSuccess = (currentBuild.currentResult ?: 'SUCCESS') == 'SUCCESS'
        def artifactsPattern = 'allure-results/**, allure-results-*/**, telegram_message.txt, telegram_should_send.txt, notify_state.json'
        if (!isSuccess) {
          artifactsPattern += ', artifacts/videos/**'
          echo 'Build is not SUCCESS: include videos in archived artifacts.'
        } else {
          echo 'Build SUCCESS: skip video artifacts to save disk.'
        }
        archiveArtifacts artifacts: artifactsPattern, allowEmptyArchive: true
      }
      script {
        try {
          // Requires Jenkins Allure plugin. If not installed, continue without failing the build.
          allure includeProperties: false, jdk: '', results: [[path: 'allure-results']]
          echo 'Allure report published in Jenkins UI.'
        } catch (Exception e) {
          echo "Allure publish skipped: ${e.getMessage()}"
        }
      }
      script {
        def notifySummary = {
          sh '''
            set +e
            pybin="python3"
            if [ -f "${PYTHON_BIN_FILE}" ]; then
              pybin="$(cat "${PYTHON_BIN_FILE}")"
            fi
            if [ ! -x "${pybin}" ] && [ "${pybin}" != "python3" ]; then
              pybin="python3"
            fi

            export ALLURE_RESULTS_DIR="allure-results"
            export RUN_URL="${BUILD_URL}"
            export ALLURE_URL="${BUILD_URL}allure/"

            "${pybin}" notify_from_allure.py || {
              echo "notify_from_allure.py failed, skip summary alert."
              exit 0
            }

            if [ ! -f telegram_should_send.txt ]; then
              echo "telegram_should_send.txt missing, skip summary alert."
              exit 0
            fi
            if [ "$(cat telegram_should_send.txt | tr -d '[:space:]')" != "1" ]; then
              echo "Summary alert disabled by notify rules."
              exit 0
            fi
            if [ ! -s telegram_message.txt ]; then
              echo "telegram_message.txt is empty, skip summary alert."
              exit 0
            fi

            "${pybin}" - <<'PY'
from pathlib import Path
from big_landing_code import send_telegram_alert

text = Path("telegram_message.txt").read_text(encoding="utf-8").strip()
if not text:
    raise SystemExit(0)

ok = send_telegram_alert(text, alert_type="summary")
raise SystemExit(0 if ok else 2)
PY
            send_rc=$?
            if [ "${send_rc}" -ne 0 ]; then
              echo "Summary alert was not delivered (check TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID and proxy)."
            fi
            exit 0
          '''
        }

        if (params.USE_TELEGRAM_PROXY) {
          withCredentials([
            string(credentialsId: 'telegram_proxy_url', variable: 'TELEGRAM_PROXY_URL'),
            string(credentialsId: 'telegram_proxy_auth_secret', variable: 'TELEGRAM_PROXY_AUTH_SECRET'),
            string(credentialsId: 'telegram_proxy_global_test', variable: 'TELEGRAM_PROXY_CREDS')
          ]) {
            notifySummary()
          }
        } else {
          notifySummary()
        }
      }
      echo "Build URL: ${env.BUILD_URL}"
      script {
        if (params.ENABLE_CONTINUOUS_LOOP) {
          def autoNextScopeMap = [
            'big_two_1of2': 'big_two_2of2',
            'big_two_2of2': 'rtk_megafon',
            'rtk_megafon': 'small_pool',
            'small_pool': 'big_two_1of2',
          ]
          int quietSeconds = 60
          try {
            quietSeconds = (params.LOOP_DELAY_SECONDS as Integer)
          } catch (Exception ignored) {
            quietSeconds = 60
          }
          if (quietSeconds < 0) {
            quietSeconds = 60
          }
          def nextJobName = (params.CHAIN_NEXT_JOB ?: '').trim()
          def nextScope = (params.CHAIN_NEXT_SCOPE ?: '').trim()
          if (!nextScope) {
            nextScope = autoNextScopeMap.get(params.PROVIDER_SCOPE as String, params.PROVIDER_SCOPE as String)
          }
          if (!nextJobName) {
            if ((params.PROVIDER_SCOPE as String) == 'release_chain') {
              nextJobName = env.JOB_NAME
            } else {
              nextJobName = nextScope
            }
          }
          echo "Continuous loop enabled. Scheduling next build: job='${nextJobName}', scope='${nextScope}', delay=${quietSeconds}s."
          build job: nextJobName,
            wait: false,
            quietPeriod: quietSeconds,
            parameters: [
              string(name: 'PROVIDER_SCOPE', value: nextScope),
              string(name: 'SITE', value: params.SITE),
              string(name: 'FORM_SUITE', value: params.FORM_SUITE),
              string(name: 'SERVICE_MODE', value: params.SERVICE_MODE),
              string(name: 'BLOCKING_PROFILE', value: params.BLOCKING_PROFILE),
              string(name: 'LOOP_DELAY_SECONDS', value: params.LOOP_DELAY_SECONDS),
              booleanParam(name: 'ENABLE_CONTINUOUS_LOOP', value: params.ENABLE_CONTINUOUS_LOOP),
              booleanParam(name: 'RUN_CHROMIUM', value: params.RUN_CHROMIUM),
              booleanParam(name: 'RUN_FIREFOX', value: params.RUN_FIREFOX),
              booleanParam(name: 'RUN_WEBKIT', value: params.RUN_WEBKIT),
              booleanParam(name: 'RUN_MOBILE_CHROMIUM', value: params.RUN_MOBILE_CHROMIUM),
              booleanParam(name: 'RUN_MOBILE_WEBKIT', value: params.RUN_MOBILE_WEBKIT),
              booleanParam(name: 'ALERT_ERRORS', value: params.ALERT_ERRORS),
              booleanParam(name: 'ALERT_AGGREGATES', value: params.ALERT_AGGREGATES),
              booleanParam(name: 'ALERT_SUMMARY', value: params.ALERT_SUMMARY),
              booleanParam(name: 'ALERT_RECOVERED', value: params.ALERT_RECOVERED),
              booleanParam(name: 'USE_TELEGRAM_PROXY', value: params.USE_TELEGRAM_PROXY),
            ]
        }
      }
      script {
        if (params.ENABLE_PERIODIC_ARTIFACT_PURGE) {
          sh '''
            set +e
            purge_every="${PERIODIC_PURGE_EVERY:-5}"
            if ! [ "${purge_every}" -ge 2 ] 2>/dev/null; then
              purge_every=5
            fi
            if ! [ "${BUILD_NUMBER}" -ge 1 ] 2>/dev/null; then
              echo "[PURGE] BUILD_NUMBER is not numeric, skip."
              exit 0
            fi
            mod=$(( BUILD_NUMBER % purge_every ))
            if [ "${mod}" -ne 0 ]; then
              echo "[PURGE] Skip: build #${BUILD_NUMBER} is not each ${purge_every}-th run."
              exit 0
            fi
            if [ -z "${JENKINS_HOME}" ] || [ -z "${JOB_NAME}" ]; then
              echo "[PURGE] JENKINS_HOME or JOB_NAME is empty, skip."
              exit 0
            fi

            job_path="${JOB_NAME//\\//\\/jobs\\/}"
            builds_dir="${JENKINS_HOME}/jobs/${job_path}/builds"
            if [ ! -d "${builds_dir}" ]; then
              echo "[PURGE] Builds dir not found: ${builds_dir}"
              exit 0
            fi

            echo "[PURGE] Running periodic purge for ${JOB_NAME} at build #${BUILD_NUMBER} (every ${purge_every})"
            find "${builds_dir}" -mindepth 2 -maxdepth 2 -type d \\( -name archive -o -name allure-report \\) ! -path "${builds_dir}/${BUILD_NUMBER}/*" -print -exec rm -rf {} +
            echo "[PURGE] Done."
            exit 0
          '''
        } else {
          echo 'Periodic artifact purge disabled by parameter.'
        }
      }
      sh '''
        set +e
        rm -rf artifacts/videos allure-results-* .pytest_cache pytest-cache-files-* __pycache__ || true
        exit 0
      '''
    }
  }
}

