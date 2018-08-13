/* This file is part of Indico.
 * Copyright (C) 2002 - 2018 European Organization for Nuclear Research (CERN).
 *
 * Indico is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 3 of the
 * License, or (at your option) any later version.
 *
 * Indico is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Indico; if not, see <http://www.gnu.org/licenses/>.
 */

import {handleAxiosError, indicoAxios} from 'indico/utils/axios';


async function _makeUrshRequest(originalURL, triggerElement) {
    const urshEndpoint = '/ursh';

    let response;
    try {
        response = await indicoAxios.post(urshEndpoint, {
            original_url: originalURL,
        });
    } catch (error) {
        handleAxiosError(error);
        return;
    }

    const data = response.data;
    if (data.success) {
        $(triggerElement).copyURLTooltip(data.msg).show();
    } else {
        $(triggerElement).qtip({
            content: {
                text: $T.gettext(`URL shortening service is unavailable: ${data.msg}`),
            },
            hide: {
                event: 'mouseleave',
                fixed: true,
                delay: 700,
            },
            show: {
                event: false,
                ready: true,
            }
        }).show();
    }
}


$(document).on('click', '.ursh-get', (event) => {
    event.preventDefault();
    const originalURL = $(event.target).attr('data-original-url');
    _makeUrshRequest(originalURL, event.target);
});
