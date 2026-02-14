import { useState } from 'react';
import { Header } from '../components/layout/Header';

export const ContactPage = () => {
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle');
    const [errorMessage, setErrorMessage] = useState('');

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setIsSubmitting(true);
        setSubmitStatus('idle');
        setErrorMessage('');

        const formData = new FormData(e.currentTarget);
        const firstName = formData.get('firstName') as string;
        const lastName = formData.get('lastName') as string;
        const email = formData.get('email') as string;
        const message = formData.get('message') as string;

        try {
            // Use the local backend API directly
            const response = await fetch('/api/contact', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    // Backend has CSRF protection but allows API calls, we might need the token if enforcement is strict
                    // For now, testing basic fetch as backend usually handles CORS/CSRF for its own domain
                },
                body: JSON.stringify({
                    firstName,
                    lastName,
                    email,
                    message
                })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Failed to send message');
            }

            setSubmitStatus('success');
            (e.target as HTMLFormElement).reset();
        } catch (err: any) {
            console.error('Contact submission error:', err);
            setSubmitStatus('error');
            setErrorMessage(err.message || 'An error occurred while sending your message. Please try again.');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen bg-momo-black text-momo-white">
            <Header />
            <main className="max-w-4xl mx-auto px-4 py-16">
                <div className="text-center mb-12">
                    <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-momo-purple to-momo-blue bg-clip-text text-transparent">
                        Contact Us
                    </h1>
                    <p className="text-momo-gray-300 text-lg">
                        Have questions or feedback? We'd love to hear from you.
                    </p>
                </div>

                <div className="max-w-xl mx-auto">
                    <div className="bg-momo-gray-800/50 backdrop-blur-xl rounded-2xl border border-momo-gray-700 p-8">
                        {submitStatus === 'success' ? (
                            <div className="text-center py-8">
                                <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                                    <svg className="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                    </svg>
                                </div>
                                <h2 className="text-2xl font-bold mb-2">Message Sent!</h2>
                                <p className="text-momo-gray-300 mb-6">
                                    Thank you for reaching out. Your message has been sent directly to our team (sumanurawat12@gmail.com and vrushcodes@gmail.com). We'll get back to you as soon as possible.
                                </p>
                                <button
                                    onClick={() => setSubmitStatus('idle')}
                                    className="text-momo-purple hover:text-momo-blue transition font-semibold"
                                >
                                    Send another message
                                </button>
                            </div>
                        ) : (
                            <form id="contact-form" onSubmit={handleSubmit} className="space-y-6">
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-momo-gray-300">First Name</label>
                                        <input
                                            type="text"
                                            name="firstName"
                                            required
                                            placeholder="Jane"
                                            className="w-full px-4 py-3 bg-momo-gray-900 border border-momo-gray-700 rounded-xl focus:ring-2 focus:ring-momo-purple/50 focus:border-momo-purple transition-all outline-none"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-momo-gray-300">Last Name</label>
                                        <input
                                            type="text"
                                            name="lastName"
                                            required
                                            placeholder="Doe"
                                            className="w-full px-4 py-3 bg-momo-gray-900 border border-momo-gray-700 rounded-xl focus:ring-2 focus:ring-momo-purple/50 focus:border-momo-purple transition-all outline-none"
                                        />
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-momo-gray-300">Email Address</label>
                                    <input
                                        type="email"
                                        name="email"
                                        required
                                        placeholder="jane@example.com"
                                        className="w-full px-4 py-3 bg-momo-gray-900 border border-momo-gray-700 rounded-xl focus:ring-2 focus:ring-momo-purple/50 focus:border-momo-purple transition-all outline-none"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-momo-gray-300">Message</label>
                                    <textarea
                                        name="message"
                                        required
                                        placeholder="How can we help?"
                                        rows={5}
                                        className="w-full px-4 py-3 bg-momo-gray-900 border border-momo-gray-700 rounded-xl focus:ring-2 focus:ring-momo-purple/50 focus:border-momo-purple transition-all outline-none resize-none"
                                    />
                                </div>

                                {submitStatus === 'error' && (
                                    <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
                                        {errorMessage}
                                    </div>
                                )}

                                <button
                                    type="submit"
                                    disabled={isSubmitting}
                                    className="w-full py-4 bg-gradient-to-r from-momo-purple to-momo-blue rounded-xl font-bold text-lg hover:opacity-90 disabled:opacity-50 transition-all shadow-lg shadow-momo-purple/20"
                                >
                                    {isSubmitting ? (
                                        <div className="flex items-center justify-center gap-2">
                                            <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
                                            <span>Sending...</span>
                                        </div>
                                    ) : (
                                        'Send Message'
                                    )}
                                </button>
                            </form>
                        )}
                    </div>
                </div>
            </main>
        </div>
    );
};
