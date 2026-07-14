// Initialize Facebook SDK
function initialize_facebook_sdk(app_id) {
    if (!app_id) return;
    
    // Only load SDK once
    if (window.FB) {
        return;
    }
    
    window.fbAsyncInit = function() {
        FB.init({
            appId: app_id,
            cookie: true,
            xfbml: true,
            version: 'v18.0'
        });
        
        // Check login status after SDK initialization
        check_facebook_login_status();
    };
    
    // Load Facebook SDK
    (function(d, s, id) {
        var js, fjs = d.getElementsByTagName(s)[0];
        if (d.getElementById(id)) return;
        js = d.createElement(s);
        js.id = id;
        js.src = "https://connect.facebook.net/en_US/sdk.js";
        fjs.parentNode.insertBefore(js, fjs);
    }(document, 'script', 'facebook-jssdk'));
}

// Check Facebook login status
function check_facebook_login_status() {
    if (!window.FB) {
        console.warn('Facebook SDK not loaded');
        return;
    }
    
    FB.getLoginStatus(function(response) {
        status_change_callback(response);
    });
}

// Handle status change callback
function status_change_callback(response) {
    if (response.status === 'connected') {
        console.log('User is logged into Facebook', response.authResponse);
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
    } else if (response.status === 'not_authorized') {
        console.log('User is logged into Facebook but not authorized for this app');
    } else {
        console.log('User is not logged into Facebook');
    }
}

frappe.ui.form.on('Facebook Settings', {
    refresh: function(frm) {
        // Set dynamic fields
        const site_url = frappe.utils.get_url();
        const expected_webhook_url = `${site_url}/api/method/social_media.facebook.api.webhook`;
        const expected_redirect_uri = `${site_url}/api/method/social_media.facebook.auth.callback`;
        
        if (frm.doc.webhook_url !== expected_webhook_url) {
            frm.set_value('webhook_url', expected_webhook_url);
        }
        if (frm.doc.redirect_uri !== expected_redirect_uri) {
            frm.set_value('redirect_uri', expected_redirect_uri);
        }

        // Initialize Facebook SDK
        if (frm.doc.app_id) {
            initialize_facebook_sdk(frm.doc.app_id);
        }
        
        // Update UI based on connection status
        update_connection_ui(frm);
        
        // Add custom buttons
        add_custom_buttons(frm);

        // Bind events to the HTML buttons in the form
        bind_html_buttons(frm);
    },

    app_id: function(frm) {
        update_redirect_uri(frm);
        // Re-initialize SDK if app ID changes
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
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Facebook Settings',
                name: 'Facebook Settings'
            },
            callback: function(r) {
                if (r.message) {
                    const site_url = frappe.utils.get_url();
                    const redirect_uri = `${site_url}/api/method/social_media.facebook.auth.callback`;
                    frm.set_value('redirect_uri', redirect_uri);
                }
            }
        });
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
        
        // Show disconnect button
        $(frm.fields_dict.disconnect_button.$wrapper).show();
        $(frm.fields_dict.disconnect_button.$wrapper).find('#disconnect-facebook').show();
        $(frm.fields_dict.connect_button.$wrapper).hide();
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
        
        // Hide disconnect button
        $(frm.fields_dict.disconnect_button.$wrapper).hide();
        $(frm.fields_dict.connect_button.$wrapper).show();
        $(frm.fields_dict.connect_button.$wrapper).find('#connect-facebook').show();
    }
}

function bind_html_buttons(frm) {
    // Connect button click
    $(frm.wrapper).find('#connect-facebook').off('click').on('click', function(e) {
        e.preventDefault();
        frappe.call({
            method: 'social_media.facebook.auth.get_oauth_url',
            callback: function(r) {
                if (r.message) {
                    const popup = window.open(r.message, '_blank', 'width=600,height=700');
                    if (!popup || popup.closed || typeof popup.closed === 'undefined') {
                        frappe.msgprint({
                            title: __('Popup Blocked'),
                            indicator: 'red',
                            message: __('Please allow popups for this site to complete the OAuth flow.')
                        });
                    }
                }
            }
        });
    });

    // Disconnect button click
    $(frm.wrapper).find('#disconnect-facebook').off('click').on('click', function(e) {
        e.preventDefault();
        frappe.confirm('Are you sure you want to disconnect from Facebook?', function() {
            frappe.call({
                method: 'social_media.facebook.auth.disconnect',
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint({
                            title: __('Disconnected'),
                            indicator: 'green',
                            message: r.message.message
                        });
                        frm.reload_doc();
                    }
                }
            });
        });
    });

    // Refresh Token button click
    $(frm.wrapper).find('#refresh-token').off('click').on('click', function(e) {
        e.preventDefault();
        frappe.call({
            method: 'social_media.facebook.doctype.facebook_settings.facebook_settings.refresh_token',
            callback: function(r) {
                if (r.message) {
                    if (r.message.success) {
                        frappe.msgprint({
                            title: __('Success'),
                            indicator: 'green',
                            message: r.message.message
                        });
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            indicator: 'red',
                            message: r.message.message
                        });
                    }
                }
            }
        });
    });
}

function add_custom_buttons(frm) {
    // Connect with Facebook button
    if (!frm.doc.is_connected) {
        frm.add_custom_button(__('Connect with Facebook'), function() {
            frappe.call({
                method: 'social_media.facebook.auth.get_oauth_url',
                callback: function(r) {
                    if (r.message) {
                        // Open OAuth URL in popup
                        const popup = window.open(r.message, '_blank', 'width=600,height=700');
                        
                        // Check if popup was blocked
                        if (!popup || popup.closed || typeof popup.closed === 'undefined') {
                            frappe.msgprint({
                                title: __('Popup Blocked'),
                                indicator: 'red',
                                message: __('Please allow popups for this site to complete the OAuth flow.')
                            });
                        }
                    }
                }
            });
        }, 'Facebook').addClass('btn-primary');

        // Manual Token button
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
                            page_access_token : values.page_access_token,
                            page_id           : values.page_id || null,
                            page_name         : values.page_name || null
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
                            }
                        }
                    });
                }
            });
            d.show();
        }, 'Facebook').addClass('btn-warning');
    } else {
        // Disconnect button
        frm.add_custom_button(__('Disconnect'), function() {
            frappe.confirm('Are you sure you want to disconnect from Facebook?', function() {
                frappe.call({
                    method: 'social_media.facebook.auth.disconnect',
                    callback: function(r) {
                        if (r.message) {
                            frappe.msgprint({
                                title: __('Disconnected'),
                                indicator: 'green',
                                message: r.message.message
                            });
                            frm.reload_doc();
                        }
                    }
                });
            });
        }, 'Facebook').addClass('btn-danger');
        
        // Test Post button
        frm.add_custom_button(__('Test Post'), function() {
            frappe.call({
                method: 'social_media.facebook.post.test_post',
                callback: function(r) {
                    if (r.message) {
                        if (r.message.success) {
                            frappe.msgprint({
                                title: __('Success'),
                                indicator: 'green',
                                message: r.message.message
                            });
                        } else {
                            frappe.msgprint({
                                title: __('Error'),
                                indicator: 'red',
                                message: r.message.error
                            });
                        }
                    }
                }
            });
        }, 'Facebook').addClass('btn-success');
        
        // Refresh Token button
        frm.add_custom_button(__('Refresh Token'), function() {
            frappe.call({
                method: 'social_media.facebook.doctype.facebook_settings.facebook_settings.refresh_token',
                callback: function(r) {
                    if (r.message) {
                        if (r.message.success) {
                            frappe.msgprint({
                                title: __('Success'),
                                indicator: 'green',
                                message: r.message.message
                            });
                        } else {
                            frappe.msgprint({
                                title: __('Error'),
                                indicator: 'red',
                                message: r.message.message
                            });
                        }
                    }
                }
            });
        }, 'Facebook').addClass('btn-warning');
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
        
        // Remove the parameter from URL
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
