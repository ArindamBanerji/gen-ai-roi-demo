import { useState, useEffect, Component, type ErrorInfo, type ReactNode } from 'react'
import { Shield, Activity, Zap, TrendingUp, FileText, ReceiptText, Scale } from 'lucide-react'
import { domainConfig } from './lib/domain'
import SOCAnalyticsTab from './components/tabs/SOCAnalyticsTab'
import RuntimeEvolutionTab from './components/tabs/RuntimeEvolutionTab'
import AlertTriageTab from './components/tabs/AlertTriageTab'
import CompoundingTab from './components/tabs/CompoundingTab'
import ExecutiveNarrativeTab from './components/tabs/ExecutiveNarrativeTab'
import S2PPreviewTab from './components/tabs/S2PPreviewTab'
import GovernanceTab from './components/tabs/GovernanceTab'

// ErrorBoundary must be a class component — hooks cannot catch render errors.
interface ErrorBoundaryState { hasError: boolean; message: string }
class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  constructor(props: { children: ReactNode }) {
    super(props)
    this.state = { hasError: false, message: '' }
  }
  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, message: error.message ?? 'Unknown error' }
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info)
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-64 gap-3 text-center">
          <p className="text-base font-semibold text-red-400">Something went wrong — reload the page</p>
          <p className="text-xs text-gray-500 font-mono max-w-lg break-all">{this.state.message}</p>
        </div>
      )
    }
    return this.props.children
  }
}

type TabId = 'soc' | 'evolution' | 'triage' | 'compounding' | 'executive' | 's2p' | 'governance'

interface Tab {
  id: TabId
  label: string
  icon: React.ReactNode
  component: React.ComponentType
  energyPercent: number
  description: string
}

const tabs: Tab[] = [
  {
    id: 'soc',
    label: 'SOC Analytics',
    icon: <Shield className="w-4 h-4" />,
    component: SOCAnalyticsTab,
    energyPercent: 20,
    description: 'Governed security metrics with provenance',
  },
  {
    id: 'evolution',
    label: 'Runtime Evolution',
    icon: <Zap className="w-4 h-4" />,
    component: RuntimeEvolutionTab,
    energyPercent: 35,
    description: 'THE KEY DIFFERENTIATOR - Decisions that make the agent smarter',
  },
  {
    id: 'triage',
    label: 'Alert Triage',
    icon: <Activity className="w-4 h-4" />,
    component: AlertTriageTab,
    energyPercent: 30,
    description: 'Graph-based reasoning with closed-loop execution',
  },
  {
    id: 'compounding',
    label: 'Compounding',
    icon: <TrendingUp className="w-4 h-4" />,
    component: CompoundingTab,
    energyPercent: 15,
    description: 'Two-loop architecture visualization',
  },
  {
    id: 'executive',
    label: 'Executive Narrative',
    icon: <FileText className="w-4 h-4" />,
    component: ExecutiveNarrativeTab,
    energyPercent: 0,
    description: 'Weekly digest for CISO — what changed, discovered, and what the system knows',
  },
  {
    id: 's2p',
    label: 'S2P Preview',
    icon: <ReceiptText className="w-4 h-4" />,
    component: S2PPreviewTab,
    energyPercent: 0,
    description: 'Same engine applied to invoice exception management',
  },
  {
    id: 'governance',
    label: 'Evidence Room',
    icon: <Scale className="w-4 h-4" />,
    component: GovernanceTab,
    energyPercent: 0,
    description: 'Governance evidence, audit chain, conservation health, and evolution trail',
  },
]

function App() {
  const [activeTab, setActiveTab] = useState<TabId>('evolution') // Start with THE differentiator

  // VIS-2: listen for cross-tab navigation events dispatched by OutcomeFeedback bridge link
  useEffect(() => {
    const handler = (e: Event) => {
      const tab = (e as CustomEvent).detail?.tab as TabId
      if (tab) setActiveTab(tab)
    }
    window.addEventListener('vis2:navigate', handler)
    return () => window.removeEventListener('vis2:navigate', handler)
  }, [])

  const ActiveComponent = tabs.find((t) => t.id === activeTab)?.component

  return (
    <div className="min-h-screen bg-soc-bg text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 bg-soc-card">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Shield className="w-8 h-8 text-soc-primary" />
              <div>
                <h1 className="text-2xl font-bold">{domainConfig.headerTitle}</h1>
                <p className="text-sm text-gray-400">
                  {domainConfig.headerSubtitle}
                </p>
              </div>
            </div>
            <div className="text-right text-sm text-gray-400">
              <div>CISO Version {domainConfig.version}</div>
              <div className="text-xs">Proving Compounding Intelligence</div>
            </div>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <nav className="border-b border-gray-800 bg-soc-card/50">
        <div className="container mx-auto px-6">
          <div className="flex gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex items-center gap-2 px-4 py-3 text-sm font-medium
                  border-b-2 transition-colors
                  ${
                    activeTab === tab.id
                      ? 'border-soc-primary text-soc-primary'
                      : 'border-transparent text-gray-400 hover:text-gray-300'
                  }
                `}
              >
                {tab.icon}
                <span>{tab.label}</span>
                {tab.id === 'evolution' && (
                  <span className="ml-1 text-xs bg-soc-secondary/20 text-soc-secondary px-2 py-0.5 rounded">
                    KEY
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Tab Description */}
      <div className="border-b border-gray-800 bg-soc-card/30">
        <div className="container mx-auto px-6 py-2">
          <p className="text-sm text-gray-400">
            {tabs.find((t) => t.id === activeTab)?.description}
          </p>
        </div>
      </div>

      {/* Tab Content */}
      <main className="container mx-auto px-6 py-6">
        {ActiveComponent && (
          <ErrorBoundary key={activeTab}>
            <ActiveComponent />
          </ErrorBoundary>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 bg-soc-card/30 mt-12">
        <div className="container mx-auto px-6 py-4 text-center text-sm text-gray-500">
          <p>
            <strong>Soundbite:</strong> "Your SIEM gets better detection rules. Our SOC
            Copilot gets <strong className="text-soc-primary">smarter</strong>."
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App
