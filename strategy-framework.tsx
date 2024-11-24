import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Users, Plus, Minus, Download, Eye, Edit } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

const users = ["Nick", "Jocelyn", "Daryl", "Pascal", "Sebastian", "Julie", "Steve"];

const predefinedObjectives = [
  "Revenue growth",
  "Pipeline growth",
  "Scale through partners",
  "Great place to work",
  "Lead Generative Integration"
];

const StrategyFramework = () => {
  const [activeUser, setActiveUser] = useState(users[0]);
  const [viewMode, setViewMode] = useState('input'); // 'input' or 'compare'
  const [userResponses, setUserResponses] = useState(
    users.reduce((acc, user) => ({
      ...acc,
      [user]: {
        aspirations: {
          purpose: '',
          objectives: predefinedObjectives.reduce((obj, objective) => ({
            ...obj,
            [objective]: {
              description: '',
              metrics: '',
              timeline: '',
              risks: '',
              dependencies: ''
            }
          }), {})
        },
        playingField: {
          geos: [''],
          segments: [''],
          partners: ['']
        },
        winningApproach: {
          valueProposition: '',
          competitiveAdvantage: '',
          activities: ['']
        },
        capabilities: {
          coreCapabilities: [''],
          supportingActivities: ['']
        },
        systems: {
          skills: [''],
          structures: [''],
          processes: ['']
        }
      }
    }), {})
  );

  const handleObjectiveFieldChange = (objective, field, value) => {
    setUserResponses(prev => ({
      ...prev,
      [activeUser]: {
        ...prev[activeUser],
        aspirations: {
          ...prev[activeUser].aspirations,
          objectives: {
            ...prev[activeUser].aspirations.objectives,
            [objective]: {
              ...prev[activeUser].aspirations.objectives[objective],
              [field]: value
            }
          }
        }
      }
    }));
  };

  const handleTextChange = (section, field, value) => {
    setUserResponses(prev => ({
      ...prev,
      [activeUser]: {
        ...prev[activeUser],
        [section]: {
          ...prev[activeUser][section],
          [field]: value
        }
      }
    }));
  };

  const handleArrayChange = (section, field, index, value) => {
    setUserResponses(prev => ({
      ...prev,
      [activeUser]: {
        ...prev[activeUser],
        [section]: {
          ...prev[activeUser][section],
          [field]: prev[activeUser][section][field].map((item, i) => 
            i === index ? value : item
          )
        }
      }
    }));
  };

  const addArrayItem = (section, field) => {
    setUserResponses(prev => ({
      ...prev,
      [activeUser]: {
        ...prev[activeUser],
        [section]: {
          ...prev[activeUser][section],
          [field]: [...prev[activeUser][section][field], '']
        }
      }
    }));
  };

  const removeArrayItem = (section, field, index) => {
    setUserResponses(prev => ({
      ...prev,
      [activeUser]: {
        ...prev[activeUser],
        [section]: {
          ...prev[activeUser][section],
          [field]: prev[activeUser][section][field].filter((_, i) => i !== index)
        }
      }
    }));
  };

  const exportData = () => {
    const dataStr = JSON.stringify(userResponses, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    const exportFileDefaultName = 'strategy-framework-data.json';

    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  const renderObjectiveInputs = (objective) => (
    <div key={objective} className="rounded-lg border p-4 space-y-4">
      <h4 className="font-medium text-lg text-blue-700">{objective}</h4>
      <div>
        <label className="block text-sm font-medium mb-2">Description</label>
        <Textarea
          value={userResponses[activeUser].aspirations.objectives[objective].description}
          onChange={(e) => handleObjectiveFieldChange(objective, 'description', e.target.value)}
          placeholder="Enter detailed description..."
          rows={3}
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-2">Key Metrics</label>
        <Textarea
          value={userResponses[activeUser].aspirations.objectives[objective].metrics}
          onChange={(e) => handleObjectiveFieldChange(objective, 'metrics', e.target.value)}
          placeholder="Define measurable targets..."
          rows={2}
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-2">Timeline</label>
        <Textarea
          value={userResponses[activeUser].aspirations.objectives[objective].timeline}
          onChange={(e) => handleObjectiveFieldChange(objective, 'timeline', e.target.value)}
          placeholder="Specify timeline and milestones..."
          rows={2}
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-2">Risks and Mitigation</label>
        <Textarea
          value={userResponses[activeUser].aspirations.objectives[objective].risks}
          onChange={(e) => handleObjectiveFieldChange(objective, 'risks', e.target.value)}
          placeholder="Identify key risks and mitigation strategies..."
          rows={2}
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-2">Dependencies</label>
        <Textarea
          value={userResponses[activeUser].aspirations.objectives[objective].dependencies}
          onChange={(e) => handleObjectiveFieldChange(objective, 'dependencies', e.target.value)}
          placeholder="List key dependencies and requirements..."
          rows={2}
        />
      </div>
    </div>
  );

  const renderComparisonView = () => (
    <div className="space-y-8">
      {predefinedObjectives.map(objective => (
        <div key={objective} className="space-y-4">
          <h3 className="text-xl font-bold text-blue-700">{objective}</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {users.map(user => (
              <Card key={user} className="border-l-4 border-l-blue-600">
                <CardHeader>
                  <CardTitle className="text-lg">{user}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {Object.entries(userResponses[user].aspirations.objectives[objective]).map(([field, value]) => (
                    <div key={field}>
                      <div className="font-medium capitalize">{field}:</div>
                      <p className="text-sm mt-1">{value || "Not specified"}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div className="max-w-6xl mx-auto p-4 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Strategy Development Framework</h1>
        <div className="flex gap-4">
          <Button
            variant={viewMode === 'input' ? 'default' : 'outline'}
            onClick={() => setViewMode('input')}
          >
            <Edit className="h-4 w-4 mr-2" />
            Input Mode
          </Button>
          <Button
            variant={viewMode === 'compare' ? 'default' : 'outline'}
            onClick={() => setViewMode('compare')}
          >
            <Eye className="h-4 w-4 mr-2" />
            Compare View
          </Button>
          <Button
            variant="outline"
            onClick={exportData}
          >
            <Download className="h-4 w-4 mr-2" />
            Export Data
          </Button>
        </div>
      </div>

      {viewMode === 'input' ? (
        <>
          <div className="bg-gray-100 p-4 rounded-lg">
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              <span className="font-medium">Current User:</span>
              <select 
                value={activeUser}
                onChange={(e) => setActiveUser(e.target.value)}
                className="border rounded p-1"
              >
                {users.map(user => (
                  <option key={user} value={user}>{user}</option>
                ))}
              </select>
            </div>
          </div>

          <Tabs defaultValue="objectives" className="space-y-6">
            <TabsList>
              <TabsTrigger value="objectives">Objectives</TabsTrigger>
              <TabsTrigger value="playingField">Playing Field</TabsTrigger>
              <TabsTrigger value="winningApproach">Winning Approach</TabsTrigger>
              <TabsTrigger value="capabilities">Capabilities</TabsTrigger>
              <TabsTrigger value="systems">Systems</TabsTrigger>
            </TabsList>

            <TabsContent value="objectives">
              <Card>
                <CardHeader>
                  <CardTitle>What are our aspirations and goals?</CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Overall Purpose
                    </label>
                    <Textarea
                      value={userResponses[activeUser].aspirations.purpose}
                      onChange={(e) => handleTextChange('aspirations', 'purpose', e.target.value)}
                      placeholder="Enter overall purpose..."
                      rows={3}
                    />
                  </div>
                  <div className="space-y-6">
                    {predefinedObjectives.map(renderObjectiveInputs)}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Other tab contents remain the same */}
          </Tabs>
        </>
      ) : (
        <div className="space-y-6">
          {renderComparisonView()}
        </div>
      )}
    </div>
  );
};

export default StrategyFramework;