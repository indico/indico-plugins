// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2025 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import manageCategoryPrompts from 'indico-url:plugin_ai_summary.manage_category_prompts';

import _ from 'lodash';
import React from 'react';
import ReactDOM from 'react-dom';
import {Form as FinalForm} from 'react-final-form';
import {Form} from 'semantic-ui-react';

import {indicoAxios} from 'indico/utils/axios';
import {FinalSubmitButton, handleSubmitError} from 'indico/react/forms';

import {FinalPromptManagerField} from './components/PromptManagerField';

export default function CategoryManagePrompts({categoryId, prompts: predefinedPrompts}) {
  const onSubmit = async ({prompts}, form) => {
    try {
      await indicoAxios.post(manageCategoryPrompts({category_id: categoryId}), {prompts});
      form.initialize({prompts});
    } catch (error) {
      handleSubmitError(error);
    }
  };

  const submitBtn = <FinalSubmitButton label="Save Changes" />;

  return (
    <FinalForm
      onSubmit={onSubmit}
      initialValues={{prompts: predefinedPrompts}}
      initialValuesEqual={_.isEqual}
      subscription={{}}
    >
      {fprops => (
        <Form onSubmit={fprops.handleSubmit}>
          <FinalPromptManagerField submitBtn={submitBtn} />
        </Form>
      )}
    </FinalForm>
  );
}

window.setupCategoryManagePrompts = function setupCategoryManagePrompts() {
  const container = document.getElementById('plugin-ai-summary-prompts');
  const categoryId = parseInt(container.dataset.categoryId, 10);
  const prompts = JSON.parse(container.dataset.prompts);
  ReactDOM.render(<CategoryManagePrompts categoryId={categoryId} prompts={prompts} />, container);
};
