;

function disable_field_based_on_value(field, value) {
    if (field.val() == value) {
        field.attr('disabled', 'disabled')
    }
}

function show_or_hide_attribute_fields(attribute_value){
    var validate_with_question_field = $('#id_validate_with_question');
    var value_field = $('#id_value');

    if(attribute_value == 'value'){
        validate_with_question_field.hide();
        validate_with_question_field.attr('disabled', 'disabled');
        value_field.show();
        value_field.attr('disabled', false);
    }
    if(attribute_value == 'validate_with_question')
    {
        validate_with_question_field.show();
        validate_with_question_field.attr('disabled', false);
        value_field.hide();
        value_field.attr('disabled', 'disabled');
    }
}
function show_or_hide_next_question(action_value) {
    show_next_question = ['SKIP_TO', 'ASK_SUBQUESTION'];

    var next_question_field = $('#id_next_question');

    if (show_next_question.indexOf(action_value) != -1) {
        next_question_field.show();
        next_question_field.attr('disabled', false)
    }
    else {
        next_question_field.hide();
        next_question_field.attr('disabled', 'disabled')
    }
}

function append_to_drop_down_options(url)
{
    counter=0;
    $.get( url, function( data ) {
        $.each(data, function() {
            $('#id_next_question').append("<option value=" + data[counter]['id'] + ">" + data[counter]['text'] +"</option>");
            counter++;
        });
    });
    }

function replace_next_question_with_right_data(questions_url) {
    if(questions_url != ""){
    $('#id_next_question').find('option')
        .remove()
        .end()
    }
    append_to_drop_down_options(questions_url)
}

function fill_questions_or_subquestions_in_next_question_field(action_value){
    var show_questions = ['SKIP_TO'];
    var show_sub_questions = ['ASK_SUBQUESTION'];

    var question_id = $('#id_question').val();
    var questions_url = "";

    if(show_questions.indexOf(action_value) != -1)
    {
        questions_url = '/questions/' + question_id +'/questions_json/'
    }
    else if (show_sub_questions.indexOf(action_value) != -1)
    {
        questions_url = '/questions/' + question_id +'/sub_questions_json/'
    }
    replace_next_question_with_right_data(questions_url);
}

jQuery(function($){
    var condition = $('#id_condition');
    var condition_value = 'EQUALS_OPTION';
    var attribute = $('#id_attribute');
    var attribute_value = 'option';
    var action_value = $('#id_action');

    disable_field_based_on_value(condition, condition_value);
    disable_field_based_on_value(attribute, attribute_value);
    show_or_hide_attribute_fields(attribute.val());
    show_or_hide_next_question(action_value.val());

    action_value.on('change', function(){
        show_or_hide_next_question($(this).val());
        fill_questions_or_subquestions_in_next_question_field(action_value.val());
    });

    attribute.on('change', function(){
        show_or_hide_attribute_fields(attribute.val());
    });

});