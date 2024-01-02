// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2024 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import renderMathInElement from 'katex/dist/contrib/auto-render.js';
import './index.css';

document.addEventListener('DOMContentLoaded', function() {
  const element = document.getElementById('notebook-wrapper');
  renderMathInElement(element, {
    delimiters: [
      {left: '$$', right: '$$', display: true},
      {left: '$', right: '$', display: false},
      {left: '\\(', right: '\\)', display: false},
      {left: '\\begin{equation}', right: '\\end{equation}', display: true},
      {left: '\\begin{align}', right: '\\end{align}', display: true},
      {left: '\\begin{alignat}', right: '\\end{alignat}', display: true},
      {left: '\\begin{gather}', right: '\\end{gather}', display: true},
      {left: '\\begin{CD}', right: '\\end{CD}', display: true},
      {left: '\\[', right: '\\]', display: true},
    ],
  });
});
