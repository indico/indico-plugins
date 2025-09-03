import React, {useCallback, useMemo, useState} from 'react';
import ReactDOM from 'react-dom';
import {Dropdown, Label, Form, TextArea, Button, Input} from 'semantic-ui-react';

export default function PromptManagerField({value, onChange}) {
  const addPrompt = () => {
    onChange([...value, {name: 'Name', text: ''}]);
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
    <Form>
      {value.map((prompt, idx) => (
        <Form.Field key={idx}>
          <Button type="button" onClick={() => removePrompt(idx)} style={{float: 'right'}}>
            Remove
          </Button>
          <label>Prompt name</label>
          <Input value={prompt.name} onChange={(_, {value: v}) => updateName(idx, v)} />
          <label>Prompt text</label>
          <TextArea value={prompt.text} onChange={(_, {value: v}) => updatePrompt(idx, v)} />
        </Form.Field>
      ))}
      <Button type="button" onClick={addPrompt}>
        Add Prompt
      </Button>
    </Form>
  );
}

export function WTFPromptManagerField({fieldId}) {
  const field = useMemo(() => document.getElementById(`${fieldId}-data`), [fieldId]);
  const [prompts, setPrompts] = useState(JSON.parse(field.value) || [{name: 'Title', text: ''}]);

  const onChange = useCallback(
    v => {
      field.value = JSON.stringify(v);
      setPrompts(v);
      field.dispatchEvent(new Event('change', {bubbles: true}));
    },
    [field]
  );

  return <PromptManagerField value={prompts} onChange={onChange} />;
}

window.setupPromptManagerFieldWidget = function setupPromptManagerFieldWidget({fieldId}) {
  ReactDOM.render(<WTFPromptManagerField fieldId={fieldId} />, document.getElementById(fieldId));
};
