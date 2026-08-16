<template>
  <div class="config-import-export">
    <div class="section-header">
      <h3 class="section-title">{{ $t('settings.importExport.title') }}</h3>
      <p class="section-desc">{{ $t('settings.importExport.description') }}</p>
    </div>

    <div class="overview-card">
      <div class="overview-item">
        <component :is="DatabaseIcon" :size="18" class="overview-icon" />
        <div class="overview-text">
          <strong>{{ availableSections.length }}</strong>
          <span>可选配置块</span>
        </div>
      </div>
      <div class="overview-item">
        <component :is="RefreshCwIcon" :size="18" class="overview-icon" />
        <div class="overview-text">
          <strong>2</strong>
          <span>导入模式</span>
        </div>
      </div>
      <div class="overview-item">
        <component :is="NetworkIcon" :size="18" class="overview-icon" />
        <div class="overview-text">
          <strong>JSON</strong>
          <span>统一迁移格式</span>
        </div>
      </div>
    </div>

    <div class="config-cards">
      <article class="config-card export-card">
        <div class="card-header">
          <div class="header-icon export">
            <DownloadIcon :size="20" />
          </div>
          <div class="header-text">
            <h4 class="card-title">{{ $t('settings.importExport.export') }}</h4>
            <p class="card-desc">{{ $t('settings.importExport.exportDesc') }}</p>
          </div>
        </div>

        <div class="card-body">
          <ul class="feature-list">
            <li>
              <CheckCircle2Icon :size="16" />
              <span>按配置块精确导出，避免把无关设置一起带走</span>
            </li>
            <li>
              <CheckCircle2Icon :size="16" />
              <span>默认不包含敏感密钥，适合发给同事或迁移环境</span>
            </li>
            <li>
              <CheckCircle2Icon :size="16" />
              <span>额外支持 Coding Plan 导出</span>
            </li>
          </ul>

          <div class="card-footer">
            <button @click="showExportDialog = true" class="action-btn primary" :disabled="isExporting">
              <DownloadIcon :size="16" />
              <span>{{ $t('settings.importExport.exportButton') }}</span>
            </button>
            <p class="footer-hint">支持全局设置和本地扩展配置</p>
          </div>
        </div>
      </article>

      <article class="config-card import-card">
        <div class="card-header">
          <div class="header-icon import">
            <UploadIcon :size="20" />
          </div>
          <div class="header-text">
            <h4 class="card-title">{{ $t('settings.importExport.import') }}</h4>
            <p class="card-desc">{{ $t('settings.importExport.importDesc') }}</p>
          </div>
        </div>

        <div class="card-body">
          <ul class="feature-list">
            <li>
              <CheckCircle2Icon :size="16" />
              <span>支持覆盖和合并两种导入策略</span>
            </li>
            <li>
              <CheckCircle2Icon :size="16" />
              <span>导入后立即应用全局设置</span>
            </li>
          </ul>

          <div class="card-footer">
            <button @click="triggerImport" class="action-btn secondary" :disabled="isImporting">
              <UploadIcon :size="16" />
              <span>{{ $t('settings.importExport.importButton') }}</span>
            </button>
            <p class="footer-hint">支持导出文件直接回填</p>
            <input
              ref="fileInput"
              type="file"
              accept=".json"
              class="hidden-input"
              @change="handleFileSelect"
            />
          </div>
        </div>
      </article>
    </div>

    <teleport to="body">
      <div v-if="showExportDialog" class="modal-overlay" @click="showExportDialog = false">
        <div class="modal-dialog" @click.stop>
          <div class="modal-header">
            <div>
              <h3 class="modal-title">{{ $t('settings.importExport.exportOptions') }}</h3>
              <p class="modal-subtitle">选择要打包的配置块，并决定是否附带敏感信息</p>
            </div>
            <button class="modal-close" @click="showExportDialog = false">
              <XIcon :size="20" />
            </button>
          </div>

          <div class="modal-body">
            <section class="panel-card warning-panel">
              <div class="panel-header">
                <div class="panel-icon">
                  <KeyIcon :size="16" />
                </div>
                <div>
                  <h4>敏感信息</h4>
                  <p>默认关闭，导出文件更适合跨机器迁移或共享给他人</p>
                </div>
              </div>

              <label class="toggle-card" :class="{ active: exportOptions.includeApiKeys }">
                <input type="checkbox" v-model="exportOptions.includeApiKeys" />
                <div class="toggle-card-main">
                  <span class="toggle-card-title">
                    <AlertTriangleIcon :size="16" class="warning-icon" />
                    {{ $t('settings.importExport.includeApiKeys') }}
                  </span>
                  <span class="toggle-card-desc">{{ $t('settings.importExport.apiKeysWarning') }}</span>
                </div>
              </label>
            </section>

            <section class="panel-card">
              <div class="panel-header">
                <div class="panel-icon">
                  <DatabaseIcon :size="16" />
                </div>
                <div>
                  <h4>{{ $t('settings.importExport.selectSections') }}</h4>
                  <p>后端配置和本地 Coding Plan 可以一起导出</p>
                </div>
              </div>

              <div class="section-grid">
                <label
                  v-for="section in availableSections"
                  :key="section.key"
                  class="section-option"
                  :class="{ selected: exportOptions.sections.includes(section.key) }"
                >
                  <input
                    type="checkbox"
                    :value="section.key"
                    v-model="exportOptions.sections"
                  />
                  <span class="section-icon">
                    <component :is="section.icon" :size="16" />
                  </span>
                  <span class="section-copy">
                    <strong>{{ getSectionLabel(section.key) }}</strong>
                    <small>{{ section.scope === 'server' ? '系统配置' : '本地扩展' }}</small>
                  </span>
                </label>
              </div>
            </section>

            <section class="summary-panel">
              <div class="summary-top">
                <span>导出摘要</span>
                <strong>已选择 {{ exportOptions.sections.length }} 个配置块</strong>
              </div>
              <div v-if="selectedSectionLabels.length" class="summary-tags">
                <span
                  v-for="label in selectedSectionLabels"
                  :key="label"
                  class="summary-tag"
                >
                  {{ label }}
                </span>
              </div>
              <p class="summary-note">
                {{ exportOptions.includeApiKeys ? '将包含敏感密钥，请谨慎存放导出文件。' : '不会导出敏感密钥，适合常规备份和迁移。' }}
              </p>
            </section>
          </div>

          <div class="modal-footer">
            <button @click="showExportDialog = false" class="btn btn-secondary">
              {{ $t('common.cancel') }}
            </button>
            <button
              @click="handleExport"
              class="btn btn-primary"
              :disabled="exportOptions.sections.length === 0 || isExporting"
            >
              <DownloadIcon :size="16" />
              <span>{{ isExporting ? '导出中...' : $t('settings.importExport.exportNow') }}</span>
            </button>
          </div>
        </div>
      </div>
    </teleport>

    <teleport to="body">
      <div v-if="showImportDialog" class="modal-overlay" @click="showImportDialog = false">
        <div class="modal-dialog" @click.stop>
          <div class="modal-header">
            <div>
              <h3 class="modal-title">{{ $t('settings.importExport.confirmImport') }}</h3>
              <p class="modal-subtitle">先确认文件内容，再决定采用合并还是覆盖策略</p>
            </div>
            <button class="modal-close" @click="showImportDialog = false">
              <XIcon :size="20" />
            </button>
          </div>

          <div class="modal-body">
            <section class="summary-panel import-summary">
              <div class="summary-grid">
                <div class="summary-item">
                  <span class="summary-item-label">{{ $t('settings.importExport.fileVersion') }}</span>
                  <strong>{{ importData?.version || '-' }}</strong>
                </div>
                <div class="summary-item">
                  <span class="summary-item-label">{{ $t('settings.importExport.exportedAt') }}</span>
                  <strong>{{ formatDate(importData?.exported_at) }}</strong>
                </div>
              </div>

              <div class="summary-section-block">
                <span class="summary-item-label">{{ $t('settings.importExport.sections') }}</span>
                <div v-if="importedSectionLabels.length" class="summary-tags">
                  <span
                    v-for="label in importedSectionLabels"
                    :key="label"
                    class="summary-tag"
                  >
                    {{ label }}
                  </span>
                </div>
                <p v-else class="summary-note">未识别到可导入的配置节</p>
              </div>

            </section>

            <div class="alert alert-warning">
              <AlertTriangleIcon :size="20" />
              <p>{{ $t('settings.importExport.importWarning') }}</p>
            </div>

            <section class="panel-card">
              <div class="panel-header">
                <div class="panel-icon">
                  <RefreshCwIcon :size="16" />
                </div>
                <div>
                  <h4>导入策略</h4>
                  <p>合并模式保留未导入内容，覆盖模式按文件内容替换当前配置</p>
                </div>
              </div>

              <label class="toggle-card" :class="{ active: importOptions.merge }">
                <input type="checkbox" v-model="importOptions.merge" />
                <div class="toggle-card-main">
                  <span class="toggle-card-title">{{ $t('settings.importExport.mergeConfig') }}</span>
                  <span class="toggle-card-desc">{{ $t('settings.importExport.mergeHint') }}</span>
                </div>
              </label>
            </section>
          </div>

          <div class="modal-footer">
            <button @click="showImportDialog = false" class="btn btn-secondary">
              {{ $t('common.cancel') }}
            </button>
            <button @click="handleImport" class="btn btn-danger" :disabled="isImporting">
              <UploadIcon :size="16" />
              <span>{{ isImporting ? '导入中...' : $t('settings.importExport.importNow') }}</span>
            </button>
          </div>
        </div>
      </div>
    </teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  AlertTriangle as AlertTriangleIcon,
  CheckCircle2 as CheckCircle2Icon,
  Cpu as CpuIcon,
  Database as DatabaseIcon,
  Download as DownloadIcon,
  Folder as FolderIcon,
  Key as KeyIcon,
  Network as NetworkIcon,
  RefreshCw as RefreshCwIcon,
  Settings as SettingsIcon,
  Upload as UploadIcon,
  User as UserIcon,
  X as XIcon,
} from 'lucide-vue-next'
import { useToast } from '@/composables/useToast'
import { configAPI, type ImportConfigResponse } from '@/api/endpoints'
import { useSettingsStore } from '@/store/settings'

type ExportSectionKey =
  | 'providers'
  | 'model'
  | 'persona'
  | 'workspace'
  | 'codingplan'

interface ConfigExportPayload {
  version: string
  exported_at: string
  app_version: string
  config: Record<string, any>
}

const BACKEND_SECTION_KEYS: ExportSectionKey[] = [
  'providers',
  'model',
  'persona',
  'workspace',
]

const CLIENT_ONLY_SECTION_KEYS = new Set<ExportSectionKey>(['codingplan'])

const toast = useToast()
const settingsStore = useSettingsStore()
const { t } = useI18n()

const fileInput = ref<HTMLInputElement>()
const showExportDialog = ref(false)
const showImportDialog = ref(false)
const isExporting = ref(false)
const isImporting = ref(false)

const exportOptions = ref<{ includeApiKeys: boolean; sections: ExportSectionKey[] }>({
  includeApiKeys: false,
  sections: ['providers', 'model', 'persona'],
})

const importOptions = ref({
  merge: false,
})

const importData = ref<ConfigExportPayload | null>(null)

const availableSections = [
  { key: 'providers' as const, icon: SettingsIcon, scope: 'server' as const },
  { key: 'model' as const, icon: CpuIcon, scope: 'server' as const },
  { key: 'persona' as const, icon: UserIcon, scope: 'server' as const },
  { key: 'workspace' as const, icon: FolderIcon, scope: 'server' as const },
  { key: 'codingplan' as const, icon: CpuIcon, scope: 'local' as const },
]

const selectedSectionLabels = computed(() => getAppliedSectionLabels(exportOptions.value.sections))
const importedSectionKeys = computed(() => Object.keys(importData.value?.config || {}) as ExportSectionKey[])
const importedSectionLabels = computed(() => getAppliedSectionLabels(importedSectionKeys.value))

function getSectionLabel(sectionKey: string): string {
  const label = t(`settings.section.${sectionKey}`)
  return label === `settings.section.${sectionKey}` ? sectionKey : label
}

function getAppliedSectionLabels(sectionKeys: string[]): string[] {
  const orderedKeys = availableSections
    .map(section => section.key)
    .filter(key => sectionKeys.includes(key))

  const knownLabels = orderedKeys.map(key => getSectionLabel(key))
  const unknownLabels = sectionKeys
    .filter(key => !orderedKeys.includes(key as ExportSectionKey))
    .map(key => getSectionLabel(key))

  return [...knownLabels, ...unknownLabels]
}

function createEmptyExportPayload(): ConfigExportPayload {
  return {
    version: '1.0.0',
    exported_at: new Date().toISOString(),
    app_version: '0.5.0',
    config: {},
  }
}

function getBackendSectionKeys(sectionKeys: ExportSectionKey[]): ExportSectionKey[] {
  return sectionKeys.filter(section => BACKEND_SECTION_KEYS.includes(section))
}

function getCodingPlanExport(includeApiKeys: boolean): Record<string, any> {
  try {
    const codingPlanConfigs = localStorage.getItem('codingPlanConfigs')
    if (!codingPlanConfigs) {
      return {}
    }

    const parsed = JSON.parse(codingPlanConfigs)
    if (!parsed || typeof parsed !== 'object') {
      return {}
    }

    if (!includeApiKeys) {
      Object.values(parsed).forEach((item: any) => {
        if (item && typeof item === 'object' && 'apiKey' in item) {
          item.apiKey = ''
        }
      })
    }

    return parsed
  } catch (error) {
    console.error('Failed to export coding plan configs:', error)
    return {}
  }
}

function downloadJsonFile(data: ConfigExportPayload) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `FBeePet_config_${new Date().toISOString().slice(0, 10)}.json`
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}

async function handleExport() {
  isExporting.value = true

  try {
    const selectedSections = [...exportOptions.value.sections]
    const backendSections = getBackendSectionKeys(selectedSections)

    const data = backendSections.length > 0
      ? await configAPI.export({
          include_api_keys: exportOptions.value.includeApiKeys,
          sections: backendSections.join(','),
        })
      : createEmptyExportPayload()

    if (selectedSections.includes('codingplan')) {
      data.config.codingplan = getCodingPlanExport(exportOptions.value.includeApiKeys)
    }

    downloadJsonFile(data)

    toast.success(
      selectedSectionLabels.value.length > 0
        ? `已导出：${selectedSectionLabels.value.join('、')}`
        : '配置导出成功',
    )
    showExportDialog.value = false
  } catch (error) {
    console.error('导出失败:', error)
    toast.error('配置导出失败')
  } finally {
    isExporting.value = false
  }
}

function triggerImport() {
  fileInput.value?.click()
}

async function handleFileSelect(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return

  try {
    const text = await file.text()
    const data = JSON.parse(text)

    if (!data?.version || !data?.config || typeof data.config !== 'object') {
      toast.error('无效的配置文件格式')
      return
    }

    importData.value = data
    showImportDialog.value = true
  } catch (error) {
    console.error('读取文件失败:', error)
    toast.error('读取配置文件失败')
  } finally {
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  }
}

function getBackendImportConfig(config: Record<string, any>): Record<string, any> {
  return Object.fromEntries(
    Object.entries(config).filter(([key]) => !CLIENT_ONLY_SECTION_KEYS.has(key as ExportSectionKey)),
  )
}

function applyCodingPlanImport(config: Record<string, any>, merge: boolean) {
  try {
    const importedConfigs = config || {}
    if (merge) {
      const existing = localStorage.getItem('codingPlanConfigs')
      const existingConfigs = existing ? JSON.parse(existing) : {}
      localStorage.setItem('codingPlanConfigs', JSON.stringify({ ...existingConfigs, ...importedConfigs }))
      return
    }

    localStorage.setItem('codingPlanConfigs', JSON.stringify(importedConfigs))
  } catch (error) {
    console.error('Failed to import coding plan configs:', error)
    throw new Error('Coding Plan 配置导入失败')
  }
}

async function handleImport() {
  if (!importData.value) return

  isImporting.value = true

  try {
    const rawConfig = JSON.parse(JSON.stringify(importData.value.config || {}))
    const rawImportedSections = Object.keys(rawConfig)
    const backendConfig = getBackendImportConfig(rawConfig)

    let response: ImportConfigResponse | null = null

    if (Object.keys(backendConfig).length > 0) {
      response = await configAPI.import({
        version: importData.value.version,
        config: backendConfig,
        merge: importOptions.value.merge,
      })

      settingsStore.settings = response.settings
    }

    if ('codingplan' in rawConfig) {
      applyCodingPlanImport(rawConfig.codingplan, importOptions.value.merge)
    }

    const appliedSectionLabels = getAppliedSectionLabels(rawImportedSections)
    const appliedMessage = appliedSectionLabels.length > 0
      ? `已应用：${appliedSectionLabels.join('、')}`
      : '已立即应用到当前运行中'

    toast.success(appliedMessage, '配置导入成功')
    showImportDialog.value = false
    importData.value = null
  } catch (error: any) {
    console.error('导入失败:', error)
    const message = error?.response?.data?.detail || error?.message || '配置导入失败'
    toast.error(message)
  } finally {
    isImporting.value = false
  }
}

function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return '-'
  try {
    return new Date(dateStr).toLocaleString()
  } catch {
    return dateStr
  }
}
</script>
<style scoped>
@import './styles/ConfigImportExport.css';
</style>
