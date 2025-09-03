// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2025 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import React from 'react';
import ReactDOM from 'react-dom';
import {Form} from 'semantic-ui-react';

export default function CategoryManagePrompts() {
  return <Form>TODO: Manage Prompts</Form>;
}

window.setupCategoryManagePrompts = function setupCategoryManagePrompts() {
  const container = document.getElementById('plugin-ai-summary-prompts');
  const categoryId = parseInt(container.dataset.categoryId, 10);
  const prompts = JSON.parse(container.dataset.prompts);
  ReactDOM.render(<CategoryManagePrompts categoryId={categoryId} prompts={prompts} />, container);
};
