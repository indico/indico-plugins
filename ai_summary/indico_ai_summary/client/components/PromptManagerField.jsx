// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2025 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import _ from 'lodash';
import React, {useCallback, useMemo, useState} from 'react';
import ReactDOM from 'react-dom';
import {Form, TextArea, Button, Input, Card, Icon} from 'semantic-ui-react';

import {FinalField} from 'indico/react/forms';

export function FinalPromptManagerField({submitBtn}) {
  return (
    <FinalField
      name="prompts"
      component={PromptManagerField}
      submitBtn={submitBtn}
      isEqual={_.isEqual}
    />
  );
}

export default function PromptManagerField({value, onChange, submitBtn}) {
  const addPrompt = () => {
    onChange([...value, {name: '', text: ''}]);
  };

  const removePrompt = idx => {
    onChange(value.filter((_, i) => i !== idx));
  };

  const updatePrompt = (idx, text) => {
    onChange(value.map((p, i) => (i === idx ? {name: p.name, text} : p)));
  };

  const updateName = (idx, name) => {
    onChange(value.map((p, i) => (i === idx ? {name, text: p.text} : p)));
  };

  return (
    <>
      {value.map((prompt, idx) => (
        <PromptField
          key={idx}
          name={prompt.name}
          text={prompt.text}
          onRemove={() => removePrompt(idx)}
          onChangeText={text => updatePrompt(idx, text)}
          onChangeName={name => updateName(idx, name)}
        />
      ))}
      <div style={{display: 'flex', justifyContent: 'end'}}>
        <Button icon type="button" labelPosition="right" onClick={addPrompt}>
          Add Prompt
          <Icon name="plus" />
        </Button>
        {submitBtn}
      </div>
    </>
  );
}

function PromptField({name, text, onChangeName, onChangeText, onRemove}) {
  return (
    <Card fluid>
      <Card.Content>
        <div style={{display: 'flex', justifyContent: 'end', marginBottom: '-1em'}}>
          <Button icon type="button" compact onClick={onRemove}>
            <Icon name="trash alternate outline" />
          </Button>
        </div>
        <Form.Field>
          <label>Prompt Name</label>
          <Input
            value={name}
            placeholder="e.g. Summarizer..."
            onChange={(_, {value: v}) => onChangeName(v)}
          />
        </Form.Field>
        <Form.Field>
          <label>Prompt Text</label>
          <TextArea
            value={text}
            placeholder="Enter your LLM prompt here..."
            onChange={(_, {value: v}) => onChangeText(v)}
            rows={10}
          />
        </Form.Field>
      </Card.Content>
    </Card>
  );
}

export function WTFPromptManagerField({fieldId}) {
  const field = useMemo(() => document.getElementById(`${fieldId}-data`), [fieldId]);
  const [prompts, setPrompts] = useState(JSON.parse(field.value));

  const onChange = useCallback(
    v => {
      field.value = JSON.stringify(v);
      setPrompts(v);
      field.dispatchEvent(new Event('change', {bubbles: true}));
    },
    [field]
  );

  return (
    <Form>
      <PromptManagerField value={prompts} onChange={onChange} />
    </Form>
  );
}

window.setupPromptManagerFieldWidget = function setupPromptManagerFieldWidget({fieldId}) {
  ReactDOM.render(<WTFPromptManagerField fieldId={fieldId} />, document.getElementById(fieldId));
};
