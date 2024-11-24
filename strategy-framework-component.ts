'use client';

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Users, Plus, Minus } from 'lucide-react';
import { PlayingFieldTab } from '@/components/playing-field-tab';

const users = ["Nick", "Jocelyn", "Daryl", "Pascal", "Sebastian", "Julie", "Steve"];

const predefinedObjectives = [
  "Revenue growth",
  "Pipeline growth",
  "Scale through partners",
  "Great place to work",
  "Lead Generative Integration"
];

export function StrategyFramework() {
  const [activeUser, setActiveUser] = useState(users[0]);
  const [userResponses, setUserResponses] = useState(
    users.reduce((acc, user) => ({
      ...acc,
      [user]: {
        aspirations: {
          purpose: '',
          objectives: predefinedObjectives.reduce((obj, objective) => ({
            ...obj,
            [objective]: {
              description: ''
            }
          }), {})
        },
        playingField: {
          geos: [''],
          segments: [''],
          partners: ['']
        }
      }
    }), {})
  );

  const handleObjectiveChange = (objective: string, value: string) => {
    setUserResponses(prev => ({
      ...prev,
      [activeUser]: {
        ...prev[activeUser],
        aspirations: {
          ...prev[activeUser].aspirations,
          objectives: {
            ...prev[activeUser].aspirations.objectives,
            [objective]: {
              description: value
            }
          }
        }
      }
    }));
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Strategy Development Framework</h1>
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5" />
          <select 
            value={activeUser}
            onChange={(e) => setActiveUser(e.target.value)}
            className="border rounded p-2"
          >
            {users.map(user => (
              <option key={user} value={user}>{user}</option>
            ))}
          </select>
        </div>
      </div>

      <Alert>
        <AlertDescription>
          Currently entering responses as {activeUser}
        </AlertDescription>
      </Alert>

      <Tabs defaultValue="aspirations" className="space-y-6">
        <TabsList>
          <TabsTrigger value="aspirations">Aspirations</TabsTrigger>
          <TabsTrigger value="playingField">Playing Field</TabsTrigger>
        </TabsList>

        <TabsContent value="aspirations">
          <Card>
            <CardHeader>
              <CardTitle>What are our aspirations and goals?</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {predefinedObjectives.map(objective => (
                <div key={objective} className="space-y-2">
                  <label className="text-sm font-medium">
                    {objective}
                  </label>
                  <Textarea
                    value={userResponses[activeUser].aspirations.objectives[objective].description}
                    onChange={(e) => handleObjectiveChange(objective, e.target.value)}
                    placeholder={`Enter details for ${objective}...`}
                    rows={3}
                  />
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="playingField">
          <PlayingFieldTab 
            activeUser={activeUser}
            userResponses={userResponses}
            setUserResponses={setUserResponses}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}