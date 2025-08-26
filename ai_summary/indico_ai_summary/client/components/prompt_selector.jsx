// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2025 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import React from 'react';
import {Dropdown, TextArea, Button, Form} from 'semantic-ui-react';
import {PROMPT_OPTIONS, buildPrompt} from '../utils/prompts';

export default function PromptSelector({
  selectedPromptKey,
  setSelectedPromptKey,
  customPromptText,
  setCustomPromptText,
  editedPromptText,
  setEditedPromptText,
  savedPrompts,
  setSavedPrompts,
  openManageModal,
  promptOnly = false,
}) {
  
  // combine predefined + saved prompts into one list for the dropdown
  const allPromptOptions = [
    ...PROMPT_OPTIONS,
    ...savedPrompts.map((prompt, idx) => ({
      key: `saved-${idx}`,
      text: prompt.slice(0, 30) + (prompt.length > 30 ? '...' : ''),
      value: `saved-${idx}`,
      promptText: prompt,
    })),
  ];

  // when user changes prompt - update selected prompt and custom text if needed
  const handlePromptChange = (_, {value}) => {
    setSelectedPromptKey(value);
    const saved = allPromptOptions.find(opt => opt.value === value && opt.promptText);
    setCustomPromptText(saved?.promptText || '');
  };

  // the full prompt text for previewing
  const promptText = selectedPromptKey.startsWith('saved-')
    ? allPromptOptions.find(opt => opt.value === selectedPromptKey)?.promptText || ''
    : buildPrompt(selectedPromptKey, customPromptText);

   if (promptOnly) {
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
          style={{marginTop: '0.3em'}}
        >
          Manage Saved Prompts
        </Button>
      </Form>
    );
  }

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
