$(function() {
    $('.vc-toolbar').dropdown({
        positioning: {
            level1: {my: 'right top', at: 'right bottom', offset: '0px 0px'}
        }
    });

    $('.vc-toolbar .action-make-owner').click(function() {
        var $this = $(this);

        $.ajax({
            url: $this.data('href'),
            method: 'POST',
            complete: IndicoUI.Dialogs.Util.progress()
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
