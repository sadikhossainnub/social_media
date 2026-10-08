import { defineStore } from 'pinia';
import { callApi } from '../api/client';

export const useComposerStore = defineStore('composer', {
  state: () => ({
    posts: [],
    mediaLibrary: [],
    loadingPosts: false,
    loadingMedia: false,
    publishing: false,
    generatingAiCaption: false,
    postForm: {
      post_type: 'Text', // Text, Image, Video, Carousel
      message: '',
      media_url: '',
      video_url: '',
      first_comment: '',
      schedule_time: '',
      variant_b_content: '',
      variant_b_image: ''
    }
  }),

  actions: {
    async fetchPosts(pageId = null) {
      this.loadingPosts = true;
      const params = {};
      if (pageId && pageId !== 'all') {
        params.page = pageId;
      }

      const res = await callApi('get_posts', params);
      this.loadingPosts = false;

      if (res.success && Array.isArray(res.data)) {
        this.posts = res.data;
      }
    },

    async fetchMediaLibrary(pageId = null) {
      this.loadingMedia = true;
      const params = {};
      if (pageId && pageId !== 'all') {
        params.page = pageId;
      }

      const res = await callApi('get_media_library', params);
      this.loadingMedia = false;

      if (res.success && Array.isArray(res.data)) {
        this.mediaLibrary = res.data;
      }
    },

    async generateCaption(topicPrompt) {
      if (!topicPrompt.trim()) return null;

      this.generatingAiCaption = true;
      const res = await callApi('generate_ai_caption', { topic: topicPrompt });
      this.generatingAiCaption = false;

      if (res.success && res.data) {
        const caption = typeof res.data === 'string' ? res.data : (res.data.caption || res.data.message);
        this.postForm.message = caption;
        return caption;
      }
      return null;
    },

    async publishPost(pageId) {
      if (!this.postForm.message.trim()) return false;

      this.publishing = true;
      const payload = {
        ...this.postForm,
        facebook_page: pageId && pageId !== 'all' ? pageId : undefined
      };

      const res = await callApi('create_post', payload);
      this.publishing = false;

      if (res.success) {
        // Reset form
        this.resetForm();
        await this.fetchPosts(pageId);
        return true;
      }
      return false;
    },

    resetForm() {
      this.postForm = {
        post_type: 'Text',
        message: '',
        media_url: '',
        video_url: '',
        first_comment: '',
        schedule_time: '',
        variant_b_content: '',
        variant_b_image: ''
      };
    }
  }
});
