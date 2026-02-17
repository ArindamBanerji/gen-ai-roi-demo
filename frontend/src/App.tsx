import { useState } from 'react'
import { Shield, Activity, Zap, TrendingUp } from 'lucide-react'
import SOCAnalyticsTab from './components/tabs/SOCAnalyticsTab'
import RuntimeEvolutionTab from './components/tabs/RuntimeEvolutionTab'
import AlertTriageTab from './components/tabs/AlertTriageTab'
import CompoundingTab from './components/tabs/CompoundingTab'

type TabId = 'soc' | 'evolution' | 'triage' | 'compounding'

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
]

function App() {
  const [activeTab, setActiveTab] = useState<TabId>('evolution') // Start with THE differentiator

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
                <h1 className="text-2xl font-bold">SOC Copilot Demo</h1>
                <p className="text-sm text-gray-400">
                  AI-Augmented Security Operations with Runtime Evolution
                </p>
              </div>
            </div>
            <div className="text-right text-sm text-gray-400">
              <div>CISO Version v1</div>
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
        {ActiveComponent && <ActiveComponent />}
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
