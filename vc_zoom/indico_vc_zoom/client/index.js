// This file is part of the Indico plugins.
// Copyright (C) 2020 - 2021 CERN and ENEA
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import {handleAxiosError, indicoAxios} from 'indico/utils/axios';

document.addEventListener('DOMContentLoaded', async () => {
  $('.vc-toolbar').dropdown({
    positioning: {
      level1: {my: 'right top', at: 'right bottom', offset: '0px 0px'},
    },
  });

  document.querySelectorAll('.vc-toolbar .action-make-host').forEach(elem => {
    elem.addEventListener('click', async () => {
      const killProgress = IndicoUI.Dialogs.Util.progress();
      try {
        await indicoAxios.post(elem.dataset.href);
        window.location.reload();
      } catch (error) {
        handleAxiosError(error);
        killProgress();
      }
    })
  })
});
