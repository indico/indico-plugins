$(function() {
    $('.event-service-row').dropdown({
        positioning: {
            level1: {my: 'right top', at: 'right bottom', offset: '0px 0px'}
        }
    });

    $('.event-service-row .action-make-moderator').click(function() {
        var $this = $(this);

        $.ajax({
            url: $this.data('href'),
            method: 'POST',
            complete: IndicoUI.Dialogs.Util.progress(),
            contentType: 'application/json',
            data: JSON.stringify({
                data: {
                    owner: ['Avatar', $('body').data('userId')]
                }
            })
        }).done(function(result) {
            if (handleAjaxError(result)) {
                return;
            } else {
                location.reload();
            }
        }).fail(function(error) {
            handleAjaxError(error);
        });
    });
});
