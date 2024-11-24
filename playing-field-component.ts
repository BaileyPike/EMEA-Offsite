'use client';

import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Plus, Minus } from 'lucide-react';

interface PlayingFieldTabProps {
  activeUser: string;
  userResponses: any; // Type this properly based on your needs
  setUserResponses: (responses: any) => void;
}

export function PlayingFieldTab({ activeUser, userResponses, setUserResponses }: PlayingFieldTabProps) {
  const handleArrayChange = (field: string, index: number, value: string) => {
    setUserResponses((prev: any) => ({
      ...prev,
      [activeUser]: {
        ...prev[activeUser],
        playingField: {
          ...prev[activeUser].playingField,
          [field]: prev[activeUser].playingField[field].map((item: string, i: number) => 
            i === index ? value : item
          )
        }
      }
    }));
  };

  const addArrayItem = (field: string) => {
    setUserResponses((prev: any) => ({
      ...prev,
      [activeUser]: {
        ...prev[activeUser],
        playingField: {
          ...prev[activeUser].playingField,
          [field]: [...prev[activeUser].playingField[field], '']
        }
      }
    }));
  };

  const removeArrayItem = (field: string, index: number) => {
    setUserResponses((prev: any) => ({
      ...prev,
      [activeUser]: {
        ...prev[activeUser],
        playingField: {
          ...prev[activeUser].playingField,
          [field]: prev[activeUser].playingField[field].filter((_: string, i: number) => i !== index)
        }
      }
    }));
  };

  const renderArrayInputs = (field: string, label: string, placeholder: string) => (
    <div className="space-y-4">
      <div className="font-medium text-sm">{label}</div>
      <div className="space-y-2">
        {userResponses[activeUser].playingField[field].map((item: string, index: number) => (
          <div key={index} className="flex gap-2">
            <Input
              value={item}
              onChange={(e) => handleArrayChange(field, index, e.target.value)}
              placeholder={placeholder}
              className="flex-1"
            />
            <Button
              variant="outline"
              size="icon"
              onClick={() => removeArrayItem(field, index)}
            >
              <Minus className="h-4 w-4" />
            </Button>
          </div>
        ))}
        <Button
          variant="outline"
          onClick={() => addArrayItem(field)}
          className="w-full"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add {label}
        </Button>
      </div>
    </div>
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Where will we play?</CardTitle>
      </CardHeader>
      <CardContent className="space-y-8">
        {renderArrayInputs(
          'geos',
          'Geographic Markets',
          'Enter target geography'
        )}

        {renderArrayInputs(
          'segments',
          'Product Categories & Segments',
          'Enter target segment'
        )}

        {renderArrayInputs(
          'partners',
          'Partners',
          'Enter key partner'
        )}
      </CardContent>
    </Card>
  );
}