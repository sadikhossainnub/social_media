function initialize_facebook_sdk(app_id, api_version) {
    if (!app_id) return;
    
    // Only load SDK once
    if (window.FB) {
        return;
    }
    
    var version = api_version || 'v21.0';
    window.fbAsyncInit = function() {
        FB.init({
            appId: app_id,
            cookie: true,
            xfbml: true,
            version: version
        });
        
        check_facebook_login_status();
    };
    
    (function(d, s, id) {
        var js, fjs = d.getElementsByTagName(s)[0];
        if (d.getElementById(id)) return;
        js = d.createElement(s);
        js.id = id;
        js.src = "https://connect.facebook.net/en_US/sdk.js";
        fjs.parentNode.insertBefore(js, fjs);
    }(document, 'script', 'facebook-jssdk'));
}

function check_facebook_login_status() {
    if (!window.FB) {
        console.warn('Facebook SDK not loaded');
        return;
    }
    
    FB.getLoginStatus(function(response) {
        status_change_callback(response);
    });
}

function status_change_callback(response) {
    if (response.status === 'connected') {
        frappe.call({
            method: 'social_media.facebook.auth.verify_facebook_login',
            args: {
                access_token: response.authResponse.accessToken,
                user_id: response.authResponse.userID
            },
            callback: function(r) {
                if (r.message && r.message.status === 'connected') {
                    console.log('Verified Facebook login');
                }
            }
        });
    }
}

frappe.ui.form.on('Facebook Settings', {
    refresh: function(frm) {
        // Set dynamic fields
        const site_url = (frappe.urllib ? frappe.urllib.get_base_url() : window.location.origin).replace(/\/$/, '');
        const expected_webhook_url = `${site_url}/api/method/social_media.facebook.api.webhook`;
        const expected_redirect_uri = `${site_url}/api/method/social_media.facebook.auth.callback`;
        
        if (frm.doc.webhook_url !== expected_webhook_url) {
            frm.set_value('webhook_url', expected_webhook_url);
        }
        if (frm.doc.redirect_uri !== expected_redirect_uri) {
            frm.set_value('redirect_uri', expected_redirect_uri);
        }

        // Style URLs
        if (frm.fields_dict.redirect_uri && frm.fields_dict.redirect_uri.input) {
            $(frm.fields_dict.redirect_uri.input).css({
                'font-family': 'monospace',
                'font-size': '13px',
                'word-break': 'break-all',
                'white-space': 'pre-wrap'
            });
        }
        if (frm.fields_dict.webhook_url && frm.fields_dict.webhook_url.input) {
            $(frm.fields_dict.webhook_url.input).css({
                'font-family': 'monospace',
                'font-size': '13px',
                'word-break': 'break-all',
                'white-space': 'pre-wrap'
            });
        }

        if (frm.doc.app_id) {
            initialize_facebook_sdk(frm.doc.app_id);
        }
        
        update_connection_ui(frm);
        add_custom_buttons(frm);
        bind_html_buttons(frm);
    },

    app_id: function(frm) {
        update_redirect_uri(frm);
        if (frm.doc.app_id) {
            initialize_facebook_sdk(frm.doc.app_id);
        }
    },

    app_secret: function(frm) {
        update_redirect_uri(frm);
    }
});

function update_redirect_uri(frm) {
    if (frm.doc.app_id && !frm.doc.redirect_uri) {
        const site_url = (frappe.urllib ? frappe.urllib.get_base_url() : window.location.origin).replace(/\/$/, '');
        const redirect_uri = `${site_url}/api/method/social_media.facebook.auth.callback`;
        frm.set_value('redirect_uri', redirect_uri);
    }
}


function update_connection_ui(frm) {
    const status_html = $(frm.fields_dict.connection_status_html.$wrapper);
    
    if (frm.doc.is_connected) {
        status_html.html(`
            <div class="alert alert-success">
                <h5>✅ Connected to Facebook</h5>
                <p><strong>Page:</strong> ${frm.doc.page_name || 'N/A'}</p>
                <p><strong>Page ID:</strong> ${frm.doc.page_id || 'N/A'}</p>
                <p><strong>Token Expiry:</strong> ${frm.doc.token_expiry ? frappe.datetime.str_to_user(frm.doc.token_expiry) : 'N/A'}</p>
            </div>
        `);
        
        if (frm.fields_dict.disconnect_button) $(frm.fields_dict.disconnect_button.$wrapper).show();
        if (frm.fields_dict.connect_button) $(frm.fields_dict.connect_button.$wrapper).hide();
    } else {
        status_html.html(`
            <div class="alert alert-info">
                <h5>👋 Facebook Integration</h5>
                <p>Click 'Connect with Facebook' to begin the OAuth flow.</p>
                <p>Make sure you have:</p>
                <ul>
                    <li>Facebook Developer App created</li>
                    <li>Valid OAuth Redirect URI configured</li>
                </ul>
            </div>
        `);
        
        if (frm.fields_dict.disconnect_button) $(frm.fields_dict.disconnect_button.$wrapper).hide();
        if (frm.fields_dict.connect_button) $(frm.fields_dict.connect_button.$wrapper).show();
    }
}

function trigger_connect_oauth() {
    // Open blank popup synchronously to bypass popup blocker
    const popup = window.open('about:blank', '_blank', 'width=600,height=700');
    frappe.call({
        method: 'social_media.facebook.auth.get_oauth_url',
        callback: function(r) {
            if (r.message && popup && !popup.closed) {
                popup.location.href = r.message;
            } else if (popup) {
                popup.close();
            }
        },
        error: function() {
            if (popup) popup.close();
        }
    });
}

function bind_html_buttons(frm) {
    // Use event delegation on frm.wrapper so handlers persist across DOM re-renders
    $(frm.wrapper).off('click', '#connect-facebook').on('click', '#connect-facebook', function(e) {
        e.preventDefault();
        trigger_connect_oauth();
    });

    $(frm.wrapper).off('click', '#disconnect-facebook').on('click', '#disconnect-facebook', function(e) {
        e.preventDefault();
        frappe.confirm(__('Are you sure you want to disconnect from Facebook?'), function() {
            frappe.call({
                method: 'social_media.facebook.doctype.facebook_settings.facebook_settings.disconnect',
                callback: function(r) {
                    frappe.show_alert({ message: __('Disconnected successfully'), indicator: 'green' });
                    frm.reload_doc();
                }
            });
        });
    });

    $(frm.wrapper).off('click', '#refresh-token').on('click', '#refresh-token', function(e) {
        e.preventDefault();
        frappe.call({
            method: 'social_media.facebook.doctype.facebook_settings.facebook_settings.refresh_token',
            callback: function(r) {
                if (r.message && r.message.success) {
                    frappe.msgprint({ title: __('Success'), indicator: 'green', message: r.message.message });
                } else if (r.message) {
                    frappe.msgprint({ title: __('Notice'), indicator: 'orange', message: r.message.message });
                }
            }
        });
    });
}

function add_custom_buttons(frm) {
    frm.clear_custom_buttons();

    if (!frm.doc.is_connected) {
        frm.add_custom_button(__('Connect with Facebook'), function() {
            trigger_connect_oauth();
        }).addClass('btn-primary');

        frm.add_custom_button(__('Set Token Manually'), function() {
            const d = new frappe.ui.Dialog({
                title: __('Set Page Access Token Manually'),
                fields: [
                    {
                        fieldname: 'info_html',
                        fieldtype: 'HTML',
                        options: `<div class="alert alert-info" style="margin-bottom:12px;">
                            <b>Get your token from:</b><br>
                            <a href="https://developers.facebook.com/tools/explorer/" target="_blank">
                                Facebook Graph API Explorer
                            </a>
                            &nbsp;→ Select your Page → Generate Token
                        </div>`
                    },
                    {
                        fieldname: 'page_access_token',
                        fieldtype: 'Small Text',
                        label: __('Page Access Token'),
                        reqd: 1,
                        description: __('Paste the Page Access Token from Graph API Explorer')
                    },
                    {
                        fieldname: 'page_id',
                        fieldtype: 'Data',
                        label: __('Page ID (optional)'),
                        description: __('Will be fetched automatically from Facebook if left blank')
                    },
                    {
                        fieldname: 'page_name',
                        fieldtype: 'Data',
                        label: __('Page Name (optional)'),
                        description: __('Will be fetched automatically from Facebook if left blank')
                    }
                ],
                primary_action_label: __('Save Token'),
                primary_action: function(values) {
                    if (!values.page_access_token) {
                        frappe.msgprint(__('Please enter a Page Access Token.'));
                        return;
                    }
                    frappe.call({
                        method: 'social_media.facebook.doctype.facebook_settings.facebook_settings.set_manual_token',
                        args: {
                            page_access_token : values.page_access_token.trim(),
                            page_id           : values.page_id ? values.page_id.trim() : null,
                            page_name         : values.page_name ? values.page_name.trim() : null
                        },
                        freeze: true,
                        freeze_message: __('Validating token with Facebook...'),
                        callback: function(r) {
                            if (r.message && r.message.success) {
                                frappe.show_alert({
                                    message: r.message.message,
                                    indicator: 'green'
                                }, 6);
                                d.hide();
                                frm.reload_doc();
                            } else if (r.message && r.message.error) {
                                frappe.msgprint({
                                    title: __('Validation Failed'),
                                    indicator: 'red',
                                    message: r.message.error
                                });
                            }
                        }
                    });
                }
            });
            d.show();
        }).addClass('btn-warning');
    } else {
        frm.add_custom_button(__('Disconnect'), function() {
            frappe.confirm(__('Are you sure you want to disconnect from Facebook?'), function() {
                frappe.call({
                    method: 'social_media.facebook.doctype.facebook_settings.facebook_settings.disconnect',
                    callback: function(r) {
                        frappe.show_alert({ message: __('Disconnected successfully'), indicator: 'green' });
                        frm.reload_doc();
                    }
                });
            });
        }).addClass('btn-danger');
        
        frm.add_custom_button(__('Test Post'), function() {
            frappe.call({
                method: 'social_media.facebook.post.test_post',
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.msgprint({
                            title: __('Success'),
                            indicator: 'green',
                            message: r.message.message
                        });
                    } else if (r.message) {
                        frappe.msgprint({
                            title: __('Error'),
                            indicator: 'red',
                            message: r.message.error || __('Test post failed')
                        });
                    }
                }
            });
        }).addClass('btn-success');
        
        frm.add_custom_button(__('Refresh Token'), function() {
            frappe.call({
                method: 'social_media.facebook.doctype.facebook_settings.facebook_settings.refresh_token',
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.msgprint({
                            title: __('Success'),
                            indicator: 'green',
                            message: r.message.message
                        });
                    } else if (r.message) {
                        frappe.msgprint({
                            title: __('Notice'),
                            indicator: 'orange',
                            message: r.message.message
                        });
                    }
                }
            });
        }).addClass('btn-warning');
    }
}

// Handle OAuth redirect success
$(document).ready(function() {
    const urlParams = new URLSearchParams(window.location.search);
    const oauth = urlParams.get('oauth');
    
    if (oauth === 'success') {
        frappe.show_alert({
            message: 'Facebook connected successfully!',
            indicator: 'green'
        }, 5);
        window.history.replaceState({}, document.title, window.location.pathname);
    } else if (oauth === 'error') {
        frappe.show_alert({
            message: 'Facebook connection failed. Please try again.',
            indicator: 'red'
        }, 5);
    } else if (oauth === 'no_code') {
        frappe.show_alert({
            message: 'No authorization code received.',
            indicator: 'red'
        }, 5);
    } else if (oauth === 'token_error') {
        frappe.show_alert({
            message: 'Failed to exchange token. Please try again.',
            indicator: 'red'
        }, 5);
    } else if (oauth === 'no_pages') {
        frappe.show_alert({
            message: 'No Facebook pages found for this account.',
            indicator: 'red'
        }, 5);
    }
});
