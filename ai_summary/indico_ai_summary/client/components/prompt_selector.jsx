// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2025 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import React from 'react';
import {Dropdown, TextArea, Form} from 'semantic-ui-react';

// dropdown + manage saved prompts button (outside card)
export function PromptControls({selectedPromptIndex, setSelectedPromptIndex, storedPrompts}) {
  const options = storedPrompts.map((prompt, idx) => ({
    key: `${idx}`,
    text: prompt.name,
    value: idx,
  }));

  const onChange = (_, {value}) => {
    setSelectedPromptIndex(value);
  };

  return (
    <Form.Field>
      <Dropdown selection options={options} value={selectedPromptIndex} onChange={onChange} />
    </Form.Field>
  );
}

export function PromptEditor({selectedPromptIndex, selectedPrompt, setPrompts}) {
  const onChange = (_, {value}) => {
    setPrompts(oldPrompts =>
      oldPrompts.map((p, i) => (i === selectedPromptIndex ? {name: p.name, text: value} : p))
    );
  };

  return (
    <Form.Field>
      <label>Selected prompt (editable)</label>
      <TextArea value={selectedPrompt.text} onChange={onChange} rows={10} />
    </Form.Field>
  );
}
