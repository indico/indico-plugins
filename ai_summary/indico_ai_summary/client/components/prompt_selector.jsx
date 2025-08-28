// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2025 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import React from 'react';
import {Dropdown, TextArea, Button, Form} from 'semantic-ui-react';
import {PROMPT_OPTIONS, buildPrompt} from '../utils/prompts';

// dropdown + manage saved prompts button (outside card)
export function PromptControls({
  selectedPromptKey,
  setSelectedPromptKey,
  savedPrompts,
  setCustomPromptText,
  openManageModal,
}) {  
  // combine predefined + saved prompts into one list for the dropdown
  const allPromptOptionsRaw = [
    ...PROMPT_OPTIONS,
    ...savedPrompts.map((prompt, idx) => ({
      key: `saved-${idx}`,
      text: prompt.slice(0, 30) + (prompt.length > 30 ? '...' : ''),
      value: `saved-${idx}`,
      promptText: prompt,
    })),
  ];

  const allPromptOptions = allPromptOptionsRaw.map(({key, text, value}) => ({key, text, value}));
  
  // when user changes prompt - update selected prompt and custom text if needed
  const handlePromptChange = (_, {value}) => {
  setSelectedPromptKey(value);
  if (value.startsWith('saved-')) {
    const saved = allPromptOptionsRaw.find(opt => opt.value === value && opt.promptText);
    setCustomPromptText(saved?.promptText || '');
  } else {
    setCustomPromptText('');
  }
};

  return (
    <Form>
      <Form.Field>
        <Dropdown
          selection
          options={allPromptOptions}
          value={selectedPromptKey}
          onChange={handlePromptChange}
        />
      </Form.Field>
      <Button
        size="tiny"
        type="button"
        onClick={openManageModal}
        style={{marginTop: '0.1em'}}
      >
        Manage Saved Prompts
      </Button>
    </Form>
  );
}

// card with custom editor + preview of prompt + generate button
export function PromptEditor({
  selectedPromptKey,
  customPromptText,
  setCustomPromptText,
  editedPromptText,
  setEditedPromptText,
  savedPrompts,
  setSavedPrompts,
}) {
  const promptText = selectedPromptKey.startsWith('saved-')
    ? savedPrompts[parseInt(selectedPromptKey.replace('saved-', ''), 10)] || ''
    : buildPrompt(selectedPromptKey, customPromptText);

  return (
    <>
      {/* custom prompt input */}
      {selectedPromptKey === 'custom' && (
        <Form.Field>
          <label>Custom prompt</label>
          <TextArea
            placeholder="Type your custom instructions…"
            value={customPromptText}
            onChange={(_, {value}) => setCustomPromptText(value)}
          />
          {/* save custom prompt to localStorage */}
          <Button
            type="button"
            size="tiny"
            onClick={() => {
              if (customPromptText.trim()) {
                const newPrompts = [...savedPrompts, customPromptText.trim()];
                setSavedPrompts(newPrompts);
                localStorage.setItem('savedPrompts', JSON.stringify(newPrompts));
              }
            }}
            style={{marginTop: '0.5em'}}
          >
            Save Custom Prompt
          </Button>
        </Form.Field>
      )}

      {/* editable preview */}
      <Form.Field>
        <label>Preview of prompt sent to the model (editable)</label>
        <TextArea
          value={editedPromptText || promptText}
          onChange={(_, {value}) => setEditedPromptText(value)}
          style={{minHeight: 140}}
        />
      </Form.Field>
    </>
  );
}
