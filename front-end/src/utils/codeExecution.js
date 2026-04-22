import axios from "axios";

export const executeCode = async (code, questionId, gameId, action = "run") => {
    const response = await axios.post(
        "http://localhost:8000/game/submit",
        {
            code,
            question_id: questionId,
            game_id: gameId,
            action,
        },
        { withCredentials: true }
    );

    return response.data;
};
